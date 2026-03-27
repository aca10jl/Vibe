"""
MoE ResNet18-UNet 模型配置
Gate: ResNet18 (3分类: 0=跳过, 1=Expert1, 2=Expert2)
Expert1: UNet-Light (轻量级)
Expert2: UNet-Heavy (重量级)
"""

# 模型配置
MODEL_CONFIG = {
    # 输入图像尺寸
    'image_height': 256,
    'image_width': 256,
    'image_channels': 3,

    # Gate: ResNet18 输出3类
    'num_classes': 3,       # 0=skip, 1=expert1, 2=expert2

    # Expert1: UNet-Light
    'expert1_base_filters': 32,     # 基础通道数 (32->64->128->256)
    'expert1_depth': 4,             # encoder/decoder 深度

    # Expert2: UNet-Heavy
    'expert2_base_filters': 64,     # 基础通道数 (64->128->256->512)
    'expert2_depth': 4,             # encoder/decoder 深度

    # UNet 输出通道 (与输入相同，做图像增强/恢复类任务)
    'output_channels': 3,

    # 推理 batch size (ATC 编译需要固定)
    'infer_batch_size': 1,
}

# 训练配置
TRAIN_CONFIG = {
    'learning_rate': 1e-3,
    'num_steps': 300,
    'train_batch_size': 4,
    'gate_loss_weight': 1.0,        # 分类损失权重
    'expert_loss_weight': 1.0,      # 专家重建损失权重
    'log_interval': 50,
}

# 输出配置
OUTPUT_CONFIG = {
    'pb_path': 'output/moe_resnet_unet_model.pb',
    'input_node': 'input_image',
    'output_nodes': ['moe/output', 'moe/gate_class'],
}
