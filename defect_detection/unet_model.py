# ==============================================================================
# UNet 编码器-解码器模型
#
# 双输入图像缺陷检测：
#   输入: test_image [1,1,448,448] UINT8 + ref_image [1,1,448,448] UINT8
#   输出: heatmap [1,1,448,448] float32, 值域 [0,1]
#
# 设计约束：
#   - 使用 tf.compat.v1 静态图
#   - 仅使用 Ascend CANN ATC 支持的算子
#   - 手动 BatchNorm（避免 FusedBatchNormV3）
#   - 基于 Tile 的上采样（避免 ResizeNearestNeighbor）
#   - 所有形状在图构建时静态确定
# ==============================================================================

import tensorflow as tf

tf.compat.v1.disable_eager_execution()
tf.compat.v1.disable_control_flow_v2()


def _dim(x, axis):
    """安全获取张量维度值（兼容 TF1/TF2）。"""
    d = x.shape[axis]
    return d.value if hasattr(d, 'value') else d


# ==============================================================================
# 基础构建块
# ==============================================================================

def _conv2d(x, out_channels, kernel_size, scope, stride=1, data_format='NCHW'):
    """
    Conv2D：手动 pad + VALID 卷积。
    算子：Pad, Conv2D（均在 ATC 白名单中）
    """
    with tf.compat.v1.variable_scope(scope):
        if data_format == 'NCHW':
            in_channels = _dim(x, 1)
        else:
            in_channels = _dim(x, 3)

        pad_size = (kernel_size - 1) // 2
        if pad_size > 0:
            if data_format == 'NCHW':
                paddings = [[0, 0], [0, 0], [pad_size, pad_size], [pad_size, pad_size]]
            else:
                paddings = [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]]
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


def _manual_batch_norm(x, num_features, scope, data_format='NCHW'):
    """
    手动 BatchNorm（推理模式）：gamma * (x - mean) / sqrt(var + eps) + beta
    算子：Sub, Mul, Rsqrt, Add, Reshape（均在 ATC 白名单中）
    不使用 tf.nn.fused_batch_norm，避免 FusedBatchNormV3 算子。
    """
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


def _conv_bn_relu(x, out_channels, kernel_size, scope, config,
                  stride=1, data_format='NCHW'):
    """Conv2D + BatchNorm + ReLU 组合块。"""
    with tf.compat.v1.variable_scope(scope):
        h = _conv2d(x, out_channels, kernel_size, "conv", stride=stride,
                    data_format=data_format)
        if config.get('unet_use_bn', True):
            h = _manual_batch_norm(h, out_channels, "bn", data_format=data_format)
        h = tf.nn.relu(h)
        return h


# ==============================================================================
# 上采样（基于 Tile，ATC 安全）
# ==============================================================================

def _upsample_2x(x, data_format='NCHW'):
    """
    2x 最近邻上采样，使用 Reshape + Tile 实现。
    算子：Reshape, Tile（均在 ATC 白名单中）

    [N,C,H,W] → reshape → [N,C,H,1,W,1] → tile [1,1,1,2,1,2] → reshape → [N,C,2H,2W]
    """
    shape = x.shape.as_list()

    if data_format == 'NCHW':
        N, C, H, W = shape
        x_reshaped = tf.reshape(x, [N, C, H, 1, W, 1])
        x_tiled = tf.tile(x_reshaped, [1, 1, 1, 2, 1, 2])
        x_up = tf.reshape(x_tiled, [N, C, H * 2, W * 2])
    else:
        N, H, W, C = shape
        x_reshaped = tf.reshape(x, [N, H, 1, W, 1, C])
        x_tiled = tf.tile(x_reshaped, [1, 1, 2, 1, 2, 1])
        x_up = tf.reshape(x_tiled, [N, H * 2, W * 2, C])

    return x_up


# ==============================================================================
# 编码器和解码器块
# ==============================================================================

def _encoder_block(x, out_channels, scope, config, data_format='NCHW'):
    """
    编码器块：两层 Conv+BN+ReLU → MaxPool 2x2 下采样。

    Returns:
        pooled: 下采样后的特征 [N, C, H/2, W/2]
        skip: 池化前的特征（用于跳跃连接）[N, C, H, W]
    """
    kernel_size = config.get('unet_kernel_size', 3)

    with tf.compat.v1.variable_scope(scope):
        h = _conv_bn_relu(x, out_channels, kernel_size, "conv1", config,
                          data_format=data_format)
        h = _conv_bn_relu(h, out_channels, kernel_size, "conv2", config,
                          data_format=data_format)
        skip = h

        if data_format == 'NCHW':
            pooled = tf.nn.max_pool2d(h, ksize=[1, 1, 2, 2], strides=[1, 1, 2, 2],
                                       padding='VALID', data_format='NCHW')
        else:
            pooled = tf.nn.max_pool2d(h, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                                       padding='VALID', data_format='NHWC')

        return pooled, skip


def _bottleneck_block(x, out_channels, scope, config, data_format='NCHW'):
    """瓶颈层：两层 Conv+BN+ReLU，不做下采样。"""
    kernel_size = config.get('unet_kernel_size', 3)

    with tf.compat.v1.variable_scope(scope):
        h = _conv_bn_relu(x, out_channels, kernel_size, "conv1", config,
                          data_format=data_format)
        h = _conv_bn_relu(h, out_channels, kernel_size, "conv2", config,
                          data_format=data_format)
        return h


def _decoder_block(x, skip, out_channels, scope, config, data_format='NCHW'):
    """
    解码器块：Tile 上采样 → skip 拼接 → 两层 Conv+BN+ReLU。
    """
    kernel_size = config.get('unet_kernel_size', 3)

    with tf.compat.v1.variable_scope(scope):
        h = _upsample_2x(x, data_format=data_format)

        # 跳跃连接拼接
        if data_format == 'NCHW':
            h = tf.concat([h, skip], axis=1)
        else:
            h = tf.concat([h, skip], axis=3)

        h = _conv_bn_relu(h, out_channels, kernel_size, "conv1", config,
                          data_format=data_format)
        h = _conv_bn_relu(h, out_channels, kernel_size, "conv2", config,
                          data_format=data_format)
        return h


# ==============================================================================
# 完整 UNet 构建
# ==============================================================================

def build_unet(test_image, ref_image, config, scope='unet'):
    """
    构建 UNet 缺陷检测模型。

    Args:
        test_image: [1, 1, 448, 448] UINT8 待检测图像
        ref_image:  [1, 1, 448, 448] UINT8 参考图像
        config: DEFECT_MODEL_CONFIG
        scope: 变量命名空间

    Returns:
        heatmap: [1, 1, 448, 448] float32, 值域 [0, 1]
        test_float: [1, 1, 448, 448] float32（归一化后的待检测图）
        ref_float:  [1, 1, 448, 448] float32（归一化后的参考图）
    """
    data_format = config.get('data_format', 'NCHW')
    enc_channels = config['unet_encoder_channels']   # [16, 32, 64, 128]
    dec_channels = config['unet_decoder_channels']    # [64, 32, 16]

    with tf.compat.v1.variable_scope(scope):
        # UINT8 → FP32 归一化
        test_float = tf.cast(test_image, tf.float32) / 255.0
        ref_float = tf.cast(ref_image, tf.float32) / 255.0

        # 双图拼接 → [1, 2, 448, 448]
        if data_format == 'NCHW':
            combined = tf.concat([test_float, ref_float], axis=1)
        else:
            combined = tf.concat([test_float, ref_float], axis=3)

        # ---- 编码器路径 ----
        # Stage 0: [1,2,448,448] → [1,16,224,224], skip0=[1,16,448,448]
        h, skip0 = _encoder_block(combined, enc_channels[0], "enc0", config,
                                   data_format=data_format)

        # Stage 1: [1,16,224,224] → [1,32,112,112], skip1=[1,32,224,224]
        h, skip1 = _encoder_block(h, enc_channels[1], "enc1", config,
                                   data_format=data_format)

        # Stage 2: [1,32,112,112] → [1,64,56,56], skip2=[1,64,112,112]
        h, skip2 = _encoder_block(h, enc_channels[2], "enc2", config,
                                   data_format=data_format)

        # Bottleneck: [1,64,56,56] → [1,128,56,56]
        h = _bottleneck_block(h, enc_channels[3], "bottleneck", config,
                               data_format=data_format)

        # ---- 解码器路径 ----
        # Stage 0: up→[1,128,112,112] + skip2→[1,192,112,112] → [1,64,112,112]
        h = _decoder_block(h, skip2, dec_channels[0], "dec0", config,
                            data_format=data_format)

        # Stage 1: up→[1,64,224,224] + skip1→[1,96,224,224] → [1,32,224,224]
        h = _decoder_block(h, skip1, dec_channels[1], "dec1", config,
                            data_format=data_format)

        # Stage 2: up→[1,32,448,448] + skip0→[1,48,448,448] → [1,16,448,448]
        h = _decoder_block(h, skip0, dec_channels[2], "dec2", config,
                            data_format=data_format)

        # ---- 输出层 ----
        # 1×1 卷积 → 单通道 + Sigmoid
        h = _conv2d(h, 1, 1, "output_conv", data_format=data_format)
        heatmap = tf.nn.sigmoid(h)

    return heatmap, test_float, ref_float
