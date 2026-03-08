# ==============================================================================
# MoE (Mixture of Experts) 路由模型定义
#
# 设计目标：
#   1. 兼容 TF2 tf.compat.v1 接口，可导出 frozen pb
#   2. 仅使用 Ascend CANN ATC 支持的算子
#   3. 静态图结构（无 Python 级动态分支），对 ATC 友好
#
# 架构：
#   Input [B,D] -> 门控网络 -> routing_probs [B,N]
#              \-> Top-K 选择 -> sparse_weights [B,N]
#               -> 所有专家并行计算 -> stacked [N,B,O]
#               -> 稀疏加权求和 -> output [B,O]
#
# 说明：
#   所有专家均参与前向计算，路由权重决定各专家对输出的贡献比例。
#   Top-K 外的专家权重为 0，等效实现"只选 K 个专家"的稀疏路由效果。
#   这种设计在静态图（pb/om）中对 ATC 工具完全兼容。
# ==============================================================================

import tensorflow as tf

# 强制使用 TF1 图模式，确保 session.run 风格可导出 pb
tf.compat.v1.disable_eager_execution()


# ==============================================================================
# 专家模型：两层 MLP，所有专家接口完全一致
# ==============================================================================

def _build_expert_v0(inputs, input_dim, hidden_dim, output_dim, scope):
    """专家类型 0：标准两层 MLP + ReLU"""
    with tf.compat.v1.variable_scope(scope):
        w1 = tf.compat.v1.get_variable(
            "w1", shape=[input_dim, hidden_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable(
            "b1", shape=[hidden_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h1 = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable(
            "w2", shape=[hidden_dim, output_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable(
            "b2", shape=[output_dim],
            initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h1, w2) + b2


def _build_expert_v1(inputs, input_dim, hidden_dim, output_dim, scope):
    """专家类型 1：带残差连接（输入维度需与 hidden_dim 匹配时使用）"""
    with tf.compat.v1.variable_scope(scope):
        # 投影层
        wp = tf.compat.v1.get_variable(
            "wp", shape=[input_dim, hidden_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        bp = tf.compat.v1.get_variable(
            "bp", shape=[hidden_dim],
            initializer=tf.compat.v1.initializers.zeros())
        proj = tf.nn.relu(tf.matmul(inputs, wp) + bp)

        # 残差块
        wr = tf.compat.v1.get_variable(
            "wr", shape=[hidden_dim, hidden_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        br = tf.compat.v1.get_variable(
            "br", shape=[hidden_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h_res = tf.nn.relu(tf.matmul(proj, wr) + br)
        h = proj + h_res  # 残差

        # 输出层
        wo = tf.compat.v1.get_variable(
            "wo", shape=[hidden_dim, output_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        bo = tf.compat.v1.get_variable(
            "bo", shape=[output_dim],
            initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h, wo) + bo


def _build_expert_v2(inputs, input_dim, hidden_dim, output_dim, scope):
    """专家类型 2：双隐层 MLP"""
    with tf.compat.v1.variable_scope(scope):
        half_dim = hidden_dim // 2

        w1 = tf.compat.v1.get_variable(
            "w1", shape=[input_dim, hidden_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable(
            "b1", shape=[hidden_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h1 = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable(
            "w2", shape=[hidden_dim, half_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable(
            "b2", shape=[half_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h2 = tf.nn.relu(tf.matmul(h1, w2) + b2)

        w3 = tf.compat.v1.get_variable(
            "w3", shape=[half_dim, output_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b3 = tf.compat.v1.get_variable(
            "b3", shape=[output_dim],
            initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h2, w3) + b3


def _build_expert_v3(inputs, input_dim, hidden_dim, output_dim, scope):
    """专家类型 3：宽浅网络（单隐层，宽度翻倍）"""
    with tf.compat.v1.variable_scope(scope):
        wide_dim = hidden_dim * 2

        w1 = tf.compat.v1.get_variable(
            "w1", shape=[input_dim, wide_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable(
            "b1", shape=[wide_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h1 = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable(
            "w2", shape=[wide_dim, output_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable(
            "b2", shape=[output_dim],
            initializer=tf.compat.v1.initializers.zeros())
        return tf.matmul(h1, w2) + b2


# 专家构建函数注册表（按 expert_id 映射）
_EXPERT_BUILDERS = [
    _build_expert_v0,
    _build_expert_v1,
    _build_expert_v2,
    _build_expert_v3,
]


def build_expert(inputs, expert_id, config):
    """构建第 expert_id 个专家模型。"""
    num_types = len(_EXPERT_BUILDERS)
    builder = _EXPERT_BUILDERS[expert_id % num_types]
    scope = f"expert_{expert_id}"
    return builder(
        inputs,
        config['input_dim'],
        config['expert_hidden_dim'],
        config['output_dim'],
        scope,
    )


# ==============================================================================
# 门控（路由）网络
# ==============================================================================

def build_gating_network(inputs, config):
    """
    轻量门控网络：输入特征 -> 各专家的路由概率。

    输出 shape: [batch, num_experts]，各行 softmax 归一化。
    """
    input_dim = config['input_dim']
    num_experts = config['num_experts']
    hidden_dim = config['gate_hidden_dim']

    with tf.compat.v1.variable_scope("gate"):
        w1 = tf.compat.v1.get_variable(
            "w1", shape=[input_dim, hidden_dim],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b1 = tf.compat.v1.get_variable(
            "b1", shape=[hidden_dim],
            initializer=tf.compat.v1.initializers.zeros())
        h = tf.nn.relu(tf.matmul(inputs, w1) + b1)

        w2 = tf.compat.v1.get_variable(
            "w2", shape=[hidden_dim, num_experts],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b2 = tf.compat.v1.get_variable(
            "b2", shape=[num_experts],
            initializer=tf.compat.v1.initializers.zeros())
        logits = tf.matmul(h, w2) + b2

        # softmax 归一化得到路由概率
        probs = tf.nn.softmax(logits, name="routing_probs")
    return probs


# ==============================================================================
# 完整 MoE 路由模型图
# ==============================================================================

def build_moe_graph(inputs, config):
    """
    构建 MoE 路由完整静态计算图。

    Args:
        inputs: tf.Tensor, shape [batch, input_dim], dtype float32
        config: dict，见 config.py MODEL_CONFIG

    Returns:
        output         : [batch, output_dim]  加权融合输出
        routing_indices: [batch, top_k]  int32，选中的专家索引
        routing_weights: [batch, top_k]  float32，选中专家的归一化权重
        routing_probs  : [batch, num_experts]  float32，全部路由概率（训练用）
    """
    num_experts = config['num_experts']
    top_k = config['top_k']

    assert top_k <= num_experts, f"top_k({top_k}) 不能超过 num_experts({num_experts})"
    assert top_k >= 1, "top_k 至少为 1"

    with tf.compat.v1.variable_scope("moe"):

        # ------------------------------------------------------------------
        # Step 1：门控网络计算路由概率
        # routing_probs: [batch, num_experts]
        # ------------------------------------------------------------------
        routing_probs = build_gating_network(inputs, config)

        # ------------------------------------------------------------------
        # Step 2：Top-K 选择
        # top_k_values : [batch, top_k]  float32
        # top_k_indices: [batch, top_k]  int32
        # ------------------------------------------------------------------
        top_k_result = tf.math.top_k(routing_probs, k=top_k, sorted=True)
        top_k_values = top_k_result.values    # [batch, top_k]
        top_k_indices = top_k_result.indices  # [batch, top_k], int32

        # ------------------------------------------------------------------
        # Step 3：对选中的 top_k 权重做归一化（使其和为 1）
        # ------------------------------------------------------------------
        weight_sum = tf.reduce_sum(top_k_values, axis=1, keepdims=True)
        # 防除零
        weight_sum = tf.maximum(weight_sum, 1e-8)
        normalized_weights = top_k_values / weight_sum  # [batch, top_k]

        # ------------------------------------------------------------------
        # Step 4：构建稀疏路由掩码矩阵 [batch, num_experts]
        #
        # 使用 tf.unstack + tf.one_hot 展开循环，在图构造时静态展开，
        # 不产生动态控制流节点，对 ATC 完全友好。
        #
        # sparse_weights[b, i] = normalized_weights[b, k] 若 expert i 被选中
        #                       = 0                        否则
        # ------------------------------------------------------------------
        # 将 [batch, top_k] 按列拆开为 top_k 个 [batch] 张量
        indices_unstacked = tf.unstack(top_k_indices, axis=1)    # list of [batch]
        weights_unstacked = tf.unstack(normalized_weights, axis=1)  # list of [batch]

        # 构建稀疏权重矩阵：从第 0 个 top-k 专家出发逐步累加
        # 避免使用 ZerosLike（规避部分 ATC 版本的算子兼容性问题）
        sparse_weights = (
            tf.one_hot(indices_unstacked[0], depth=num_experts, dtype=tf.float32)
            * tf.expand_dims(weights_unstacked[0], axis=1)
        )  # [batch, num_experts]

        for k_idx in range(1, top_k):
            # 为第 k_idx 个选中专家生成 one-hot [batch, num_experts]
            one_hot_k = tf.one_hot(
                indices_unstacked[k_idx],  # [batch]
                depth=num_experts,
                dtype=tf.float32,
            )
            # 权重列向量 [batch, 1]
            weight_k = tf.expand_dims(weights_unstacked[k_idx], axis=1)
            sparse_weights = sparse_weights + one_hot_k * weight_k

        # ------------------------------------------------------------------
        # Step 5：所有专家并行前向计算
        # 每个专家输出 [batch, output_dim]
        # ------------------------------------------------------------------
        expert_outputs = []
        for i in range(num_experts):
            expert_out = build_expert(inputs, i, config)
            expert_outputs.append(expert_out)

        # stack -> [num_experts, batch, output_dim]
        stacked_experts = tf.stack(expert_outputs, axis=0)

        # ------------------------------------------------------------------
        # Step 6：稀疏加权求和
        #
        # sparse_weights: [batch, num_experts]
        # 转置并扩维: [num_experts, batch, 1]
        # 与 stacked_experts 逐元素相乘后在 num_experts 轴上求和
        # 结果: [batch, output_dim]
        # ------------------------------------------------------------------
        # [num_experts, batch]
        weights_T = tf.transpose(sparse_weights)
        # [num_experts, batch, 1]
        weights_exp = tf.expand_dims(weights_T, axis=2)
        # [num_experts, batch, output_dim]
        weighted = stacked_experts * weights_exp
        # [batch, output_dim]
        combined = tf.reduce_sum(weighted, axis=0)

        # ------------------------------------------------------------------
        # Step 7：命名输出节点（ATC 需要用到节点名）
        # ------------------------------------------------------------------
        output = tf.identity(combined, name="output")
        routing_indices_out = tf.identity(top_k_indices, name="routing_indices")
        routing_weights_out = tf.identity(normalized_weights, name="routing_weights")
        # 路由概率：训练时用于负载均衡损失
        routing_probs_out = tf.identity(routing_probs, name="routing_probs_aux")

    return output, routing_indices_out, routing_weights_out, routing_probs_out
