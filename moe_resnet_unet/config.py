# ==============================================================================
# MoE ResNet18 + UNet 专家组合模型配置
#
# 路由器: ResNet18 (3分类)
#   - 类别 0: 跳过计算（返回全零）
#   - 类别 1: 轻量 UNet 专家
#   - 类别 2: 重量 UNet 专家
#
# 适配 Ascend CANN ATC 工具编译 om 离线推理模型
# ==============================================================================

MODEL_CONFIG = {
    # --- 输入规格 ---
    'image_shape': [1, 3, 224, 224],   # NCHW, batch=1 固定
    'data_format': 'NCHW',

    # --- 路由器（ResNet18 3分类）---
    'num_classes': 3,                   # 0=跳过, 1=轻量UNet, 2=重量UNet

    # --- 轻量 UNet 专家（expert1）---
    'unet_light_channels': [8, 16, 32, 64],
    'unet_light_bottleneck': 128,

    # --- 重量 UNet 专家（expert2）---
    'unet_heavy_channels': [16, 32, 64, 128],
    'unet_heavy_bottleneck': 256,

    # --- UNet 输出通道（分割掩码）---
    'unet_output_channels': 1,

    # --- ATC 部署参数 ---
    'infer_batch_size': 1,
}

TRAIN_CONFIG = {
    'learning_rate': 1e-4,
    'num_steps': 2000,
    'train_batch_size': 4,
    'router_loss_weight': 1.0,         # 路由分类损失权重
    'expert_loss_weight': 1.0,         # 专家分割损失权重
    'lb_loss_weight': 0.01,            # 负载均衡辅助损失权重
    'log_interval': 200,
}

OUTPUT_CONFIG = {
    'pb_path': 'output/moe_resnet_unet_model.pb',
    'input_node': 'input_image',
    'output_nodes': [
        'moe/output',
        'moe/routing_class',
    ],
}
