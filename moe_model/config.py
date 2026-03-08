# ==============================================================================
# MoE (Mixture of Experts) 路由模型配置
# 适配 Ascend CANN ATC 工具编译 om 离线推理模型
# ==============================================================================

MODEL_CONFIG = {
    # --- 输入/输出维度 ---
    'input_dim': 128,          # 输入特征维度
    'output_dim': 64,          # 输出维度（所有专家模型接口统一）

    # --- MoE 路由参数 ---
    'num_experts': 4,          # 专家模型数量
    'top_k': 2,                # 每次路由激活的专家数量（1 或 2）

    # --- 门控网络结构 ---
    'gate_hidden_dim': 64,     # 门控网络隐藏层维度（轻量化设计）

    # --- 专家网络结构（每个专家两层 MLP）---
    'expert_hidden_dim': 256,  # 专家隐藏层维度

    # --- ATC 部署参数 ---
    # ATC 编译要求固定 batch_size，推理时统一使用该值
    # atc 命令示例：--input_shape="input_tensor:1,128"
    'infer_batch_size': 1,
}

TRAIN_CONFIG = {
    'learning_rate': 1e-3,
    'num_steps': 500,          # 演示用，可增大
    'train_batch_size': 32,
    'lb_loss_weight': 0.01,    # 负载均衡辅助损失权重
    'log_interval': 100,
}

OUTPUT_CONFIG = {
    'pb_path': 'output/moe_model.pb',
    # ATC 转换时的输入/输出节点名
    'input_node': 'input_tensor',
    'output_nodes': [
        'moe/output',            # 主输出：加权融合后的特征 [batch, output_dim]
        'moe/routing_indices',   # 路由结果：选中的专家索引 [batch, top_k]
        'moe/routing_weights',   # 路由权重：选中专家的归一化权重 [batch, top_k]
    ],
}

# ATC 转换命令参考（Ascend 310/910）：
# atc --model=output/moe_model.pb \
#     --framework=3 \
#     --output=output/moe_model \
#     --input_shape="input_tensor:1,128" \
#     --input_format=ND \
#     --output_type=FP32 \
#     --log=info \
#     --soc_version=Ascend310
