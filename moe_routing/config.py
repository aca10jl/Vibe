# ==============================================================================
# MoE 路由模型配置
# 适配 Ascend CANN ATC 工具编译 om 离线推理模型
# ==============================================================================

MODEL_CONFIG = {
    # --- 输入/输出维度 ---
    'input_dim': 128,
    'output_dim': 64,

    # --- MoE 路由参数 ---
    'num_experts': 4,
    'top_k': 2,                # 最多激活的专家数（1 或 2）

    # --- 门控网络结构 ---
    'gate_hidden_dim': 64,

    # --- 专家网络结构 ---
    'expert_hidden_dim': 256,

    # --- 置信度阈值 ---
    # 当 top-1 专家置信度超过此值时只用 1 个专家，否则用 2 个
    'confidence_threshold': 0.7,

    # --- ATC 部署参数 ---
    'infer_batch_size': 1,
}

TRAIN_CONFIG = {
    'learning_rate': 1e-3,
    'num_steps': 500,
    'train_batch_size': 32,
    'lb_loss_weight': 0.01,
    'log_interval': 100,
}

OUTPUT_CONFIG = {
    'pb_path': 'output/moe_routing_model.pb',
    'input_node': 'input_tensor',
    'output_nodes': [
        'moe/output',
        'moe/routing_indices',
        'moe/routing_weights',
    ],
}
