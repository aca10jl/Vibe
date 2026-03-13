# ==============================================================================
# MoE 路由模型 V2 —— 基于 tf.cond 的稀疏条件执行
#
# 改进：
#   - 完整支持 top_k=1 和 top_k=2
#   - 支持用户注册自定义专家（从 PyTorch 转换的 pb 或自定义 builder）
#   - 无自定义专家时使用内置默认专家
#   - 图像检测场景：双输入 UINT8 [1,1,448,448] -> 输出 UINT8 [1,1,448,448]
#
# 设计约束：
#   - 使用 tf.compat.v1 静态图，可导出 frozen pb
#   - 仅使用 Ascend CANN ATC 支持的算子
#   - tf.cond 生成 Switch/Merge 节点，ATC 可识别
#   - 固定 batch_size=1 用于推理
# ==============================================================================

import tensorflow as tf

tf.compat.v1.disable_eager_execution()
# 使用 TF1 风格控制流（生成 Switch/Merge 节点），ATC 兼容性更好
tf.compat.v1.disable_control_flow_v2()


# ==============================================================================
# 内置默认专家模型（当用户未提供自定义专家时使用）
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


DEFAULT_EXPERT_BUILDERS = [_build_expert_v0, _build_expert_v1, _build_expert_v2, _build_expert_v3]


# ==============================================================================
# 专家注册表 —— 支持用户自定义专家
# ==============================================================================

class ExpertRegistry:
    """
    专家注册表，管理 MoE 路由中可用的专家模型。

    用户可以注册自定义专家 builder 函数（例如从 PyTorch 转换而来）。
    未注册时使用内置默认专家。

    用法：
        registry = ExpertRegistry(num_experts=4)

        # 注册自定义专家（可选）
        registry.register(0, my_custom_builder)
        registry.register(2, another_builder)
        # 专家 1、3 将使用默认 builder

        # 获取构建函数
        builder = registry.get_builder(0)  # 返回 my_custom_builder
        builder = registry.get_builder(1)  # 返回默认 _build_expert_v1
    """

    def __init__(self, num_experts):
        self.num_experts = num_experts
        self._custom_builders = {}

    def register(self, expert_id, builder_fn):
        """
        注册自定义专家 builder。

        Args:
            expert_id: 专家编号 (0 ~ num_experts-1)
            builder_fn: callable(inputs, input_dim, hidden_dim, output_dim, scope) -> tensor
        """
        if expert_id < 0 or expert_id >= self.num_experts:
            raise ValueError(f"expert_id {expert_id} 超出范围 [0, {self.num_experts})")
        self._custom_builders[expert_id] = builder_fn

    def get_builder(self, expert_id):
        """获取专家的 builder 函数，优先返回自定义 builder。"""
        if expert_id in self._custom_builders:
            return self._custom_builders[expert_id]
        return DEFAULT_EXPERT_BUILDERS[expert_id % len(DEFAULT_EXPERT_BUILDERS)]

    def has_custom(self, expert_id):
        return expert_id in self._custom_builders

    def summary(self):
        lines = []
        for i in range(self.num_experts):
            src = "自定义" if self.has_custom(i) else "默认"
            name = self.get_builder(i).__name__
            lines.append(f"  专家 {i}: [{src}] {name}")
        return "\n".join(lines)


# 全局默认注册表
_global_registry = None


def get_registry(num_experts):
    global _global_registry
    if _global_registry is None or _global_registry.num_experts != num_experts:
        _global_registry = ExpertRegistry(num_experts)
    return _global_registry


def set_registry(registry):
    global _global_registry
    _global_registry = registry


# ==============================================================================
# 门控网络
# ==============================================================================

def build_gating_network(inputs, config):
    """轻量门控网络：特征输入 -> 各专家路由概率 [batch, num_experts]"""
    input_dim = config['gate_input_dim']
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
# 基于 tf.cond 的条件专家执行
# ==============================================================================

def _cond_expert(inputs, expert_id, is_selected, config, registry=None):
    """
    使用 tf.cond 条件执行单个专家。

    被选中时执行专家前向计算，否则返回全零张量。
    """
    if registry is None:
        registry = get_registry(config['num_experts'])
    builder = registry.get_builder(expert_id)
    scope = f"expert_{expert_id}"
    output_dim = config['gate_input_dim']
    input_dim = config['gate_input_dim']
    batch_size = config['infer_batch_size']

    def true_fn():
        return builder(inputs, input_dim, config['expert_hidden_dim'], output_dim, scope)

    def false_fn():
        return tf.zeros([batch_size, output_dim], dtype=tf.float32)

    return tf.cond(is_selected, true_fn, false_fn, name=f"cond_expert_{expert_id}")


# ==============================================================================
# 完整 MoE 图构建（支持 top_k=1 和 top_k=2）
# ==============================================================================

def build_moe_graph(inputs, config, registry=None):
    """
    构建基于 tf.cond 的 MoE 路由计算图。

    完整支持 top_k=1 和 top_k=2：
      - top_k=1: 始终只用 1 个专家，权重固定为 [1.0]
      - top_k=2: 当 top-1 置信度 >= threshold 时用 1 个，否则用 2 个

    Args:
        inputs: [batch, gate_input_dim] placeholder
        config: MODEL_CONFIG dict
        registry: ExpertRegistry，可选

    Returns:
        output, routing_indices, routing_weights, routing_probs
    """
    num_experts = config['num_experts']
    top_k = config['top_k']
    threshold = config.get('confidence_threshold', 0.7)
    output_dim = config['gate_input_dim']

    if registry is None:
        registry = get_registry(num_experts)

    with tf.compat.v1.variable_scope("moe"):

        # Step 1: 门控网络
        routing_probs = build_gating_network(inputs, config)

        # Step 2: Top-K 选择
        top_k_result = tf.math.top_k(routing_probs, k=top_k, sorted=True)
        top_k_values = top_k_result.values      # [batch, top_k]
        top_k_indices = top_k_result.indices     # [batch, top_k]

        # Step 3: 提取 top-1 索引和置信度
        top1_idx = top_k_indices[0, 0]
        top1_conf = top_k_values[0, 0]

        if top_k == 1:
            # ============ Top-K = 1 模式 ============
            # 始终只激活 1 个专家，权重固定为 1.0
            normalized_weights = tf.constant([[1.0]], dtype=tf.float32)

            expert_outputs = []
            for i in range(num_experts):
                is_selected = tf.equal(top1_idx, tf.constant(i, dtype=tf.int32))
                expert_out = _cond_expert(inputs, i, is_selected, config, registry)
                expert_outputs.append(expert_out)

            # 加权求和（只有 1 个非零）
            combined = tf.zeros([config['infer_batch_size'], output_dim], dtype=tf.float32)
            for i in range(num_experts):
                is_top1 = tf.equal(top1_idx, tf.constant(i, dtype=tf.int32))
                w_i = tf.cond(is_top1,
                              lambda: tf.constant(1.0),
                              lambda: tf.constant(0.0),
                              name=f"weight_expert_{i}")
                w_expanded = tf.reshape(w_i, [1, 1])
                combined = combined + expert_outputs[i] * w_expanded

        else:
            # ============ Top-K = 2 模式 ============
            top2_idx = top_k_indices[0, 1]

            # 置信度判断
            use_single_expert = tf.greater_equal(top1_conf, threshold,
                                                 name="use_single_expert")

            # 归一化权重
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

            # 条件执行各专家
            expert_outputs = []
            for i in range(num_experts):
                expert_i = tf.constant(i, dtype=tf.int32)
                is_top1 = tf.equal(top1_idx, expert_i)
                is_top2 = tf.logical_and(
                    tf.equal(top2_idx, expert_i),
                    tf.logical_not(use_single_expert),
                )
                is_selected = tf.logical_or(is_top1, is_top2)
                expert_out = _cond_expert(inputs, i, is_selected, config, registry)
                expert_outputs.append(expert_out)

            # 加权融合
            combined = tf.zeros([config['infer_batch_size'], output_dim], dtype=tf.float32)
            for i in range(num_experts):
                expert_i = tf.constant(i, dtype=tf.int32)
                w_i = tf.case(
                    [
                        (tf.equal(top1_idx, expert_i), lambda k=0: normalized_weights[0, k]),
                        (tf.equal(top2_idx, expert_i), lambda k=1: normalized_weights[0, k]),
                    ],
                    default=lambda: tf.constant(0.0, dtype=tf.float32),
                    name=f"weight_expert_{i}",
                )
                w_expanded = tf.reshape(w_i, [1, 1])
                combined = combined + expert_outputs[i] * w_expanded

        # 命名输出节点
        output = tf.identity(combined, name="output")
        routing_indices_out = tf.identity(top_k_indices, name="routing_indices")
        routing_weights_out = tf.identity(normalized_weights, name="routing_weights")
        routing_probs_out = tf.identity(routing_probs, name="routing_probs_aux")

    return output, routing_indices_out, routing_weights_out, routing_probs_out


# ==============================================================================
# 训练用图（所有专家均参与，用于梯度计算）
# ==============================================================================

def build_moe_graph_train(inputs, config, registry=None):
    """
    训练模式：所有专家均前向计算，通过稀疏权重实现软路由。
    支持 top_k=1 和 top_k=2。
    """
    num_experts = config['num_experts']
    top_k = config['top_k']

    if registry is None:
        registry = get_registry(num_experts)

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
        input_dim = config['gate_input_dim']
        expert_outputs = []
        for i in range(num_experts):
            builder = registry.get_builder(i)
            scope = f"expert_{i}"
            out = builder(inputs, input_dim, config['expert_hidden_dim'],
                          input_dim, scope)
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
