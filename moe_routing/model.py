# ==============================================================================
# MoE 路由模型 —— 基于 tf.cond 的真正稀疏条件执行
#
# 核心思路：
#   1. 门控网络输出路由概率 [batch, num_experts]
#   2. Top-K 选择出 1~2 个最优专家
#   3. 对每个专家，使用 tf.cond 判断是否被选中
#      - 被选中：执行专家前向计算
#      - 未被选中：直接返回零张量（跳过计算）
#   4. 加权融合被选中专家的输出
#
# 设计约束：
#   - 使用 tf.compat.v1 静态图，可导出 frozen pb
#   - 仅使用 Ascend CANN ATC 支持的算子
#   - tf.cond 在 TF 静态图中生成 Switch/Merge 节点，ATC 可识别
#   - 固定 batch_size=1 用于推理（ATC 要求静态形状）
# ==============================================================================

import tensorflow as tf

tf.compat.v1.disable_eager_execution()
# 使用 TF1 风格控制流（生成 Switch/Merge 节点），ATC 兼容性更好
tf.compat.v1.disable_control_flow_v2()


# ==============================================================================
# 专家模型定义
# ==============================================================================

def _build_expert_v0(inputs, input_dim, hidden_dim, output_dim, scope):
    """标准两层 MLP + ReLU"""
    with tf.compat.v1.variable_scope(scope):
        w1 = tf.compat.v1.get_variable("w1", [input_dim, hidden_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable("b1", [hidden_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        h = tf.nn.relu(tf.matmul(inputs, w1) + b1)
        w2 = tf.compat.v1.get_variable("w2", [hidden_dim, output_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable("b2", [output_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h, w2) + b2


def _build_expert_v1(inputs, input_dim, hidden_dim, output_dim, scope):
    """带残差连接的 MLP"""
    with tf.compat.v1.variable_scope(scope):
        wp = tf.compat.v1.get_variable("wp", [input_dim, hidden_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        bp = tf.compat.v1.get_variable("bp", [hidden_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        proj = tf.nn.relu(tf.matmul(inputs, wp) + bp)

        wr = tf.compat.v1.get_variable("wr", [hidden_dim, hidden_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        br = tf.compat.v1.get_variable("br", [hidden_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        h_res = tf.nn.relu(tf.matmul(proj, wr) + br)
        h = proj + h_res

        wo = tf.compat.v1.get_variable("wo", [hidden_dim, output_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        bo = tf.compat.v1.get_variable("bo", [output_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h, wo) + bo


def _build_expert_v2(inputs, input_dim, hidden_dim, output_dim, scope):
    """双隐层 MLP"""
    with tf.compat.v1.variable_scope(scope):
        half = hidden_dim // 2
        w1 = tf.compat.v1.get_variable("w1", [input_dim, hidden_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable("b1", [hidden_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        h1 = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable("w2", [hidden_dim, half],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable("b2", [half],
                                        initializer=tf.compat.v1.initializers.zeros())
        h2 = tf.nn.relu(tf.matmul(h1, w2) + b2)

        w3 = tf.compat.v1.get_variable("w3", [half, output_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b3 = tf.compat.v1.get_variable("b3", [output_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h2, w3) + b3


def _build_expert_v3(inputs, input_dim, hidden_dim, output_dim, scope):
    """宽浅网络（单隐层，宽度翻倍）"""
    with tf.compat.v1.variable_scope(scope):
        wide = hidden_dim * 2
        w1 = tf.compat.v1.get_variable("w1", [input_dim, wide],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable("b1", [wide],
                                        initializer=tf.compat.v1.initializers.zeros())
        h = tf.nn.relu(tf.matmul(inputs, w1) + b1)
        w2 = tf.compat.v1.get_variable("w2", [wide, output_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable("b2", [output_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h, w2) + b2


_EXPERT_BUILDERS = [_build_expert_v0, _build_expert_v1, _build_expert_v2, _build_expert_v3]


# ==============================================================================
# 门控网络
# ==============================================================================

def build_gating_network(inputs, config):
    """轻量门控网络：输入 -> 各专家路由概率 [batch, num_experts]"""
    input_dim = config['input_dim']
    num_experts = config['num_experts']
    hidden_dim = config['gate_hidden_dim']

    with tf.compat.v1.variable_scope("gate"):
        w1 = tf.compat.v1.get_variable("w1", [input_dim, hidden_dim],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable("b1", [hidden_dim],
                                        initializer=tf.compat.v1.initializers.zeros())
        h = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable("w2", [hidden_dim, num_experts],
                                        initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable("b2", [num_experts],
                                        initializer=tf.compat.v1.initializers.zeros())
        logits = tf.matmul(h, w2) + b2
        probs = tf.nn.softmax(logits, name="routing_probs")
    return probs


# ==============================================================================
# 基于 tf.cond 的条件专家执行（核心创新）
# ==============================================================================

def _cond_expert(inputs, expert_id, is_selected, config):
    """
    使用 tf.cond 条件执行单个专家。

    如果 is_selected 为 True，执行该专家的前向计算；
    否则返回全零张量，完全跳过该专家的矩阵运算。

    在 TF 静态图中，tf.cond 生成 Switch/Merge 控制流节点，
    运行时只执行被选中的分支，实现真正的计算节省。

    Args:
        inputs: [batch, input_dim]
        expert_id: 专家编号
        is_selected: 标量 bool tensor
        config: 模型配置

    Returns:
        expert_output: [batch, output_dim]，未被选中时为零张量
    """
    builder = _EXPERT_BUILDERS[expert_id % len(_EXPERT_BUILDERS)]
    scope = f"expert_{expert_id}"
    output_dim = config['output_dim']
    input_dim = config['input_dim']

    # tf.cond 要求两个分支返回相同形状的张量
    # 使用固定 batch_size=1 来确保静态形状（ATC 推理场景）
    batch_size = config['infer_batch_size']

    def true_fn():
        """被选中：执行专家前向计算"""
        return builder(inputs, input_dim, config['expert_hidden_dim'], output_dim, scope)

    def false_fn():
        """未被选中：返回固定形状零张量"""
        return tf.zeros([batch_size, output_dim], dtype=tf.float32)

    return tf.cond(is_selected, true_fn, false_fn, name=f"cond_expert_{expert_id}")


# ==============================================================================
# 完整 MoE 图构建
# ==============================================================================

def build_moe_graph(inputs, config):
    """
    构建基于 tf.cond 的 MoE 路由计算图。

    支持动态 top-1/top-2 路由：
      - 当 top-1 专家置信度 >= threshold 时，只激活 1 个专家
      - 否则激活 top-2 个专家

    Args:
        inputs: [batch, input_dim] placeholder
        config: MODEL_CONFIG dict

    Returns:
        output: [batch, output_dim] 最终输出
        routing_indices: [batch, top_k] 选中的专家索引
        routing_weights: [batch, top_k] 归一化权重
        routing_probs: [batch, num_experts] 完整路由概率（训练用）
    """
    num_experts = config['num_experts']
    top_k = config['top_k']
    threshold = config.get('confidence_threshold', 0.7)

    with tf.compat.v1.variable_scope("moe"):

        # Step 1: 门控网络
        routing_probs = build_gating_network(inputs, config)

        # Step 2: Top-K 选择
        top_k_result = tf.math.top_k(routing_probs, k=top_k, sorted=True)
        top_k_values = top_k_result.values      # [batch, top_k]
        top_k_indices = top_k_result.indices     # [batch, top_k]

        # Step 3: 置信度判断 —— top-1 专家是否足够自信
        # top1_conf: 标量（batch=1 时）
        top1_conf = top_k_values[0, 0]
        use_single_expert = tf.greater_equal(top1_conf, threshold,
                                             name="use_single_expert")

        # Step 4: 构建归一化权重
        # 当只用 1 个专家时，权重为 [1.0, 0.0]
        # 当用 2 个专家时，权重按比例归一化
        weight_sum = tf.reduce_sum(top_k_values, axis=1, keepdims=True)
        weight_sum = tf.maximum(weight_sum, 1e-8)
        normalized_weights_2 = top_k_values / weight_sum

        single_weights = tf.constant([[1.0, 0.0]], dtype=tf.float32)

        normalized_weights = tf.cond(
            use_single_expert,
            lambda: single_weights,
            lambda: normalized_weights_2,
            name="select_weights",
        )

        # Step 5: 条件执行各专家
        # 对每个专家检查是否在 top-k 中被选中
        # 使用标量索引比较（batch=1 推理场景）
        expert_outputs = []
        for i in range(num_experts):
            expert_i = tf.constant(i, dtype=tf.int32)
            top1_idx = top_k_indices[0, 0]
            top2_idx = top_k_indices[0, 1]

            # 专家 i 是否是 top-1
            is_top1 = tf.equal(top1_idx, expert_i)
            # 专家 i 是否是 top-2（且确实使用了 2 个专家）
            is_top2 = tf.logical_and(
                tf.equal(top2_idx, expert_i),
                tf.logical_not(use_single_expert),
            )
            is_selected = tf.logical_or(is_top1, is_top2)

            expert_out = _cond_expert(inputs, i, is_selected, config)
            expert_outputs.append(expert_out)

        # Step 6: 加权融合
        # 对被选中的专家输出乘以对应权重并求和
        # 构建权重映射：每个专家的实际权重
        expert_weight_list = []
        for i in range(num_experts):
            expert_i = tf.constant(i, dtype=tf.int32)
            top1_idx = top_k_indices[0, 0]
            top2_idx = top_k_indices[0, 1]

            # 获取专家 i 对应的权重
            w_i = tf.case(
                [
                    (tf.equal(top1_idx, expert_i), lambda k=0: normalized_weights[0, k]),
                    (tf.equal(top2_idx, expert_i), lambda k=1: normalized_weights[0, k]),
                ],
                default=lambda: tf.constant(0.0, dtype=tf.float32),
                name=f"weight_expert_{i}",
            )
            expert_weight_list.append(w_i)

        # 加权求和
        combined = tf.zeros_like(expert_outputs[0])
        for i in range(num_experts):
            w_expanded = tf.reshape(expert_weight_list[i], [1, 1])
            combined = combined + expert_outputs[i] * w_expanded

        # Step 7: 命名输出节点
        output = tf.identity(combined, name="output")
        routing_indices_out = tf.identity(top_k_indices, name="routing_indices")
        routing_weights_out = tf.identity(normalized_weights, name="routing_weights")
        routing_probs_out = tf.identity(routing_probs, name="routing_probs_aux")

    return output, routing_indices_out, routing_weights_out, routing_probs_out


# ==============================================================================
# 训练用图（所有专家均参与，用于梯度计算）
# ==============================================================================

def build_moe_graph_train(inputs, config):
    """
    训练模式：所有专家均前向计算，通过稀疏权重实现软路由。

    训练时不使用 tf.cond 跳过专家，因为需要所有专家接收梯度，
    避免未被选中的专家永远不更新。

    推理导出时使用 build_moe_graph（含 tf.cond 条件执行）。
    """
    num_experts = config['num_experts']
    top_k = config['top_k']

    with tf.compat.v1.variable_scope("moe"):
        routing_probs = build_gating_network(inputs, config)

        top_k_result = tf.math.top_k(routing_probs, k=top_k, sorted=True)
        top_k_values = top_k_result.values
        top_k_indices = top_k_result.indices

        weight_sum = tf.reduce_sum(top_k_values, axis=1, keepdims=True)
        weight_sum = tf.maximum(weight_sum, 1e-8)
        normalized_weights = top_k_values / weight_sum

        # 稀疏权重矩阵
        indices_unstacked = tf.unstack(top_k_indices, axis=1)
        weights_unstacked = tf.unstack(normalized_weights, axis=1)

        sparse_weights = (
            tf.one_hot(indices_unstacked[0], depth=num_experts, dtype=tf.float32)
            * tf.expand_dims(weights_unstacked[0], axis=1)
        )
        for k_idx in range(1, top_k):
            one_hot_k = tf.one_hot(indices_unstacked[k_idx], depth=num_experts, dtype=tf.float32)
            weight_k = tf.expand_dims(weights_unstacked[k_idx], axis=1)
            sparse_weights = sparse_weights + one_hot_k * weight_k

        # 所有专家均计算
        expert_outputs = []
        for i in range(num_experts):
            builder = _EXPERT_BUILDERS[i % len(_EXPERT_BUILDERS)]
            scope = f"expert_{i}"
            out = builder(inputs, config['input_dim'], config['expert_hidden_dim'],
                          config['output_dim'], scope)
            expert_outputs.append(out)

        stacked = tf.stack(expert_outputs, axis=0)

        weights_T = tf.transpose(sparse_weights)
        weights_exp = tf.expand_dims(weights_T, axis=2)
        weighted = stacked * weights_exp
        combined = tf.reduce_sum(weighted, axis=0)

        output = tf.identity(combined, name="output")
        routing_indices_out = tf.identity(top_k_indices, name="routing_indices")
        routing_weights_out = tf.identity(normalized_weights, name="routing_weights")
        routing_probs_out = tf.identity(routing_probs, name="routing_probs_aux")

    return output, routing_indices_out, routing_weights_out, routing_probs_out
