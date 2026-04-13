# ==============================================================================
# 缺陷检测模型配置
# 适配 Ascend CANN ATC 工具编译 om 离线推理模型
#
# 架构：UNet（主模型） + ResNet（子模型） + MoR Router（路由器）
# ==============================================================================

DEFECT_MODEL_CONFIG = {
    # --- 输入规格 ---
    'image_height': 448,
    'image_width': 448,
    'image_channels': 1,          # 单通道灰度图
    'data_format': 'NCHW',
    'infer_batch_size': 1,

    # --- UNet 编码器-解码器架构 ---
    'unet_encoder_channels': [16, 32, 64, 128],   # 4 级编码器通道数
    'unet_decoder_channels': [64, 32, 16],         # 3 级解码器通道数
    'unet_input_channels': 2,     # 双图拼接（待检测图 + 参考图）
    'unet_kernel_size': 3,
    'unet_use_bn': True,

    # --- 4×4 固定网格切分（MoR Router） ---
    'grid_rows': 4,
    'grid_cols': 4,
    # 派生: patch_h = 448 // 4 = 112, patch_w = 448 // 4 = 112
    'refinement_threshold': 0.3,  # heatmap 区域最大值超过此阈值时触发 ResNet
    'attenuation_mode': 'score',  # 'score': heatmap *= resnet_score（分数衰减）

    # --- ResNet 轻量级分类器 ---
    'resnet_input_channels': 3,   # heatmap_patch + test_patch + ref_patch
    'resnet_base_channels': 16,   # 基础通道数（轻量级，控制图大小）
    'resnet_num_blocks': [2, 2, 2, 2],  # ResNet-18 风格：4 阶段各 2 个残差块
}

DEFECT_TRAIN_CONFIG = {
    'learning_rate': 1e-4,
    'num_steps_unet': 1000,       # UNet 训练步数
    'num_steps_resnet': 500,      # ResNet 训练步数
    'train_batch_size': 4,
    'log_interval': 100,
    'unet_loss_weight': 1.0,
    'resnet_loss_weight': 0.5,
}

DEFECT_OUTPUT_CONFIG = {
    'pb_path': 'output/defect_detection_model.pb',
    'input_nodes': {
        'test_image': 'input_test_image',      # [1,1,448,448] UINT8
        'ref_image': 'input_ref_image',         # [1,1,448,448] UINT8
    },
    'output_nodes': [
        'defect_detection/refined_heatmap',     # [1,1,448,448] float32
        'defect_detection/raw_heatmap',         # [1,1,448,448] float32（MoR 前的原始 heatmap）
    ],
}
