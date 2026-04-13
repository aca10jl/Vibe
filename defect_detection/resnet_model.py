# ==============================================================================
# 轻量级 ResNet-18 分类器
#
# Patch 级别缺陷/非缺陷二分类：
#   输入: [1, 3, 112, 112] float32（heatmap_patch + test_patch + ref_patch）
#   输出: 标量 float32, 值域 [0, 1]（缺陷概率）
#
# 设计约束：
#   - 轻量级（base_channels=16），因为在 MoR 中被 16 个 tf.cond 分支引用
#   - 使用 tf.AUTO_REUSE 实现权重共享
#   - 仅使用 ATC 白名单算子
#   - 手动 BatchNorm
# ==============================================================================

import tensorflow as tf

tf.compat.v1.disable_eager_execution()
tf.compat.v1.disable_control_flow_v2()


def _dim(x, axis):
    """安全获取张量维度值（兼容 TF1/TF2）。"""
    d = x.shape[axis]
    return d.value if hasattr(d, 'value') else d


# ==============================================================================
# 基础构建块（与 unet_model.py 共用模式，但独立实现避免循环导入）
# ==============================================================================

def _conv2d_resnet(x, out_channels, kernel_size, scope, stride=1,
                   data_format='NCHW'):
    """Conv2D，手动 pad + VALID 卷积。"""
    with tf.compat.v1.variable_scope(scope):
        if data_format == 'NCHW':
            in_channels = _dim(x, 1)
        else:
            in_channels = _dim(x, 3)

        pad_size = (kernel_size - 1) // 2
        if pad_size > 0:
            if data_format == 'NCHW':
                paddings = [[0, 0], [0, 0], [pad_size, pad_size],
                            [pad_size, pad_size]]
            else:
                paddings = [[0, 0], [pad_size, pad_size],
                            [pad_size, pad_size], [0, 0]]
            x = tf.pad(x, paddings)

        kernel = tf.compat.v1.get_variable(
            "kernel", [kernel_size, kernel_size, in_channels, out_channels],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        bias = tf.compat.v1.get_variable(
            "bias", [out_channels],
            initializer=tf.compat.v1.initializers.zeros())

        if stride > 1:
            if data_format == 'NCHW':
                strides = [1, 1, stride, stride]
            else:
                strides = [1, stride, stride, 1]
        else:
            strides = [1, 1, 1, 1]

        h = tf.nn.conv2d(x, kernel, strides=strides, padding='VALID',
                         data_format=data_format)

        if data_format == 'NCHW':
            h = h + tf.reshape(bias, [1, -1, 1, 1])
        else:
            h = h + bias

        return h


def _bn_resnet(x, num_features, scope, data_format='NCHW'):
    """手动 BatchNorm，避免 FusedBatchNormV3。"""
    with tf.compat.v1.variable_scope(scope):
        gamma = tf.compat.v1.get_variable(
            "gamma", [num_features],
            initializer=tf.compat.v1.initializers.ones())
        beta = tf.compat.v1.get_variable(
            "beta", [num_features],
            initializer=tf.compat.v1.initializers.zeros())
        moving_mean = tf.compat.v1.get_variable(
            "moving_mean", [num_features],
            initializer=tf.compat.v1.initializers.zeros(),
            trainable=False)
        moving_var = tf.compat.v1.get_variable(
            "moving_var", [num_features],
            initializer=tf.compat.v1.initializers.ones(),
            trainable=False)

        if data_format == 'NCHW':
            gamma_r = tf.reshape(gamma, [1, -1, 1, 1])
            beta_r = tf.reshape(beta, [1, -1, 1, 1])
            mean_r = tf.reshape(moving_mean, [1, -1, 1, 1])
            var_r = tf.reshape(moving_var, [1, -1, 1, 1])
        else:
            gamma_r = gamma
            beta_r = beta
            mean_r = moving_mean
            var_r = moving_var

        return gamma_r * (x - mean_r) * tf.math.rsqrt(var_r + 1e-5) + beta_r


def _conv_bn_relu_resnet(x, out_channels, kernel_size, scope,
                         stride=1, data_format='NCHW'):
    """Conv + BN + ReLU。"""
    with tf.compat.v1.variable_scope(scope):
        h = _conv2d_resnet(x, out_channels, kernel_size, "conv",
                           stride=stride, data_format=data_format)
        h = _bn_resnet(h, out_channels, "bn", data_format=data_format)
        h = tf.nn.relu(h)
        return h


# ==============================================================================
# 残差块
# ==============================================================================

def _residual_block(x, out_channels, scope, downsample=False,
                    data_format='NCHW'):
    """
    基本残差块（ResNet-18 风格）：
    两层 Conv3x3+BN + 残差连接 + ReLU

    downsample=True 时：
    - 第一个卷积使用 stride=2
    - shortcut 使用 1x1 conv stride=2 调整维度
    """
    if data_format == 'NCHW':
        in_channels = _dim(x, 1)
    else:
        in_channels = _dim(x, 3)

    stride = 2 if downsample else 1

    with tf.compat.v1.variable_scope(scope):
        # 主路径
        h = _conv2d_resnet(x, out_channels, 3, "conv1", stride=stride,
                           data_format=data_format)
        h = _bn_resnet(h, out_channels, "bn1", data_format=data_format)
        h = tf.nn.relu(h)

        h = _conv2d_resnet(h, out_channels, 3, "conv2", stride=1,
                           data_format=data_format)
        h = _bn_resnet(h, out_channels, "bn2", data_format=data_format)

        # Shortcut 路径
        if downsample or in_channels != out_channels:
            shortcut = _conv2d_resnet(x, out_channels, 1, "shortcut_conv",
                                      stride=stride, data_format=data_format)
            shortcut = _bn_resnet(shortcut, out_channels, "shortcut_bn",
                                  data_format=data_format)
        else:
            shortcut = x

        # 残差连接
        h = h + shortcut
        h = tf.nn.relu(h)

        return h


def _resnet_stage(x, out_channels, num_blocks, scope, downsample_first=True,
                  data_format='NCHW'):
    """一个 ResNet 阶段：多个残差块，第一个可选下采样。"""
    with tf.compat.v1.variable_scope(scope):
        h = _residual_block(x, out_channels, "block0",
                            downsample=downsample_first,
                            data_format=data_format)
        for i in range(1, num_blocks):
            h = _residual_block(h, out_channels, f"block{i}",
                                downsample=False, data_format=data_format)
        return h


# ==============================================================================
# ResNet 分类器
# ==============================================================================

def build_resnet_classifier(patch_input, config, scope='resnet'):
    """
    构建轻量级 ResNet-18 分类器。

    Args:
        patch_input: [1, 3, patch_h, patch_w] float32
                     通道 0: heatmap patch
                     通道 1: test image patch
                     通道 2: reference image patch
        config: DEFECT_MODEL_CONFIG
        scope: 变量命名空间

    Returns:
        score: [1, 1] float32, 值域 [0, 1]（缺陷概率）

    使用 tf.AUTO_REUSE 以支持 MoR 中 16 个 tf.cond 分支共享权重。

    架构 (patch_h=patch_w=112):
        初始层: Conv3x3+BN+ReLU → [1, 16, 112, 112]
        Stage1: 2 blocks, ch=16,  无下采样 → [1, 16, 112, 112]
        Stage2: 2 blocks, ch=32,  下采样   → [1, 32, 56, 56]
        Stage3: 2 blocks, ch=64,  下采样   → [1, 64, 28, 28]
        Stage4: 2 blocks, ch=128, 下采样   → [1, 128, 14, 14]
        GAP: [1, 128]
        FC: 128 → 1 + Sigmoid
    """
    data_format = config.get('data_format', 'NCHW')
    base_ch = config.get('resnet_base_channels', 16)
    num_blocks = config.get('resnet_num_blocks', [2, 2, 2, 2])

    with tf.compat.v1.variable_scope(scope, reuse=tf.compat.v1.AUTO_REUSE):
        # 初始卷积层
        h = _conv_bn_relu_resnet(patch_input, base_ch, 3, "stem",
                                 data_format=data_format)

        # Stage 1: 无下采样
        h = _resnet_stage(h, base_ch, num_blocks[0], "stage1",
                          downsample_first=False, data_format=data_format)

        # Stage 2: 下采样 → [1, 32, 56, 56]
        h = _resnet_stage(h, base_ch * 2, num_blocks[1], "stage2",
                          downsample_first=True, data_format=data_format)

        # Stage 3: 下采样 → [1, 64, 28, 28]
        h = _resnet_stage(h, base_ch * 4, num_blocks[2], "stage3",
                          downsample_first=True, data_format=data_format)

        # Stage 4: 下采样 → [1, 128, 14, 14]
        h = _resnet_stage(h, base_ch * 8, num_blocks[3], "stage4",
                          downsample_first=True, data_format=data_format)

        # Global Average Pooling → [1, 128]
        if data_format == 'NCHW':
            h = tf.reduce_mean(h, axis=[2, 3])
        else:
            h = tf.reduce_mean(h, axis=[1, 2])

        # FC: 128 → 1
        fc_in_dim = base_ch * 8
        w_fc = tf.compat.v1.get_variable(
            "fc/kernel", [fc_in_dim, 1],
            initializer=tf.compat.v1.initializers.glorot_uniform())
        b_fc = tf.compat.v1.get_variable(
            "fc/bias", [1],
            initializer=tf.compat.v1.initializers.zeros())
        h = tf.matmul(h, w_fc) + b_fc

        # Sigmoid → [0, 1]
        score = tf.nn.sigmoid(h)

    return score
