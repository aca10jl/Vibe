# ==============================================================================
# MoE ResNet18 路由器 + UNet 专家组合模型
#
# 架构：
#   - 路由器: ResNet18（3分类）
#       - 类别 0: 跳过计算（返回全零）
#       - 类别 1: 轻量 UNet 专家（少通道，低复杂度）
#       - 类别 2: 重量 UNet 专家（多通道，高复杂度）
#   - 专家: UNet 编码-解码结构 + skip connections
#
# 设计约束：
#   - 使用 tf.compat.v1 静态图，可导出 frozen pb
#   - 仅使用 Ascend CANN ATC 支持的算子
#   - tf.cond / tf.case 生成 Switch/Merge 节点，ATC 可识别
#   - 固定 batch_size=1 用于推理
# ==============================================================================

import tensorflow as tf

tf.compat.v1.disable_eager_execution()
tf.compat.v1.disable_control_flow_v2()


# ==============================================================================
# 基础算子
# ==============================================================================

def _conv2d(x, out_channels, kernel_size, stride, scope, data_format='NCHW',
            use_bias=True):
    """卷积层，使用 get_variable 创建权重。"""
    with tf.compat.v1.variable_scope(scope):
        if data_format == 'NCHW':
            in_channels = x.get_shape().as_list()[1]
            strides = [1, 1, stride, stride]
        else:
            in_channels = x.get_shape().as_list()[-1]
            strides = [1, stride, stride, 1]

        kernel = tf.compat.v1.get_variable(
            "kernel",
            [kernel_size, kernel_size, in_channels, out_channels],
            initializer=tf.compat.v1.initializers.he_normal(),
        )
        padding = 'SAME' if kernel_size > 1 else 'VALID'
        h = tf.nn.conv2d(x, kernel, strides=strides, padding=padding,
                         data_format=data_format)
        if use_bias:
            bias = tf.compat.v1.get_variable(
                "bias", [out_channels],
                initializer=tf.compat.v1.initializers.zeros(),
            )
            if data_format == 'NCHW':
                bias_reshape = tf.reshape(bias, [1, out_channels, 1, 1])
            else:
                bias_reshape = tf.reshape(bias, [1, 1, 1, out_channels])
            h = h + bias_reshape
        return h


def _batch_norm(x, is_training, scope, data_format='NCHW'):
    """Batch Normalization，兼容训练和推理模式。"""
    with tf.compat.v1.variable_scope(scope):
        if data_format == 'NCHW':
            num_channels = x.get_shape().as_list()[1]
        else:
            num_channels = x.get_shape().as_list()[-1]

        gamma = tf.compat.v1.get_variable(
            "gamma", [num_channels],
            initializer=tf.compat.v1.initializers.ones(),
        )
        beta = tf.compat.v1.get_variable(
            "beta", [num_channels],
            initializer=tf.compat.v1.initializers.zeros(),
        )
        moving_mean = tf.compat.v1.get_variable(
            "moving_mean", [num_channels],
            initializer=tf.compat.v1.initializers.zeros(),
            trainable=False,
        )
        moving_variance = tf.compat.v1.get_variable(
            "moving_variance", [num_channels],
            initializer=tf.compat.v1.initializers.ones(),
            trainable=False,
        )

        if is_training:
            h, batch_mean, batch_var = tf.compat.v1.nn.fused_batch_norm(
                x, gamma, beta,
                data_format=data_format,
                is_training=True,
            )
            # 更新移动平均
            decay = 0.9
            update_mean = moving_mean.assign(
                moving_mean * decay + batch_mean * (1 - decay))
            update_var = moving_variance.assign(
                moving_variance * decay + batch_var * (1 - decay))
            with tf.control_dependencies([update_mean, update_var]):
                h = tf.identity(h)
        else:
            h, _, _ = tf.compat.v1.nn.fused_batch_norm(
                x, gamma, beta,
                mean=moving_mean,
                variance=moving_variance,
                data_format=data_format,
                is_training=False,
            )
        return h


def _maxpool2d(x, pool_size=2, stride=2, data_format='NCHW'):
    """最大池化。"""
    if data_format == 'NCHW':
        ksize = [1, 1, pool_size, pool_size]
        strides = [1, 1, stride, stride]
    else:
        ksize = [1, pool_size, pool_size, 1]
        strides = [1, stride, stride, 1]
    return tf.nn.max_pool2d(x, ksize=ksize, strides=strides, padding='SAME',
                            data_format=data_format)


def _global_avg_pool(x, data_format='NCHW'):
    """全局平均池化。"""
    if data_format == 'NCHW':
        return tf.reduce_mean(x, axis=[2, 3])
    else:
        return tf.reduce_mean(x, axis=[1, 2])


def _upsample_nearest(x, scale=2, data_format='NCHW'):
    """最近邻上采样（NCHW 需要转换格式）。"""
    if data_format == 'NCHW':
        x_nhwc = tf.transpose(x, [0, 2, 3, 1])
    else:
        x_nhwc = x

    shape = tf.shape(x_nhwc)
    new_h = shape[1] * scale
    new_w = shape[2] * scale
    x_up = tf.compat.v1.image.resize_nearest_neighbor(x_nhwc, [new_h, new_w])

    if data_format == 'NCHW':
        return tf.transpose(x_up, [0, 3, 1, 2])
    return x_up


def _concat(tensors, data_format='NCHW'):
    """沿通道维度拼接。"""
    axis = 1 if data_format == 'NCHW' else 3
    return tf.concat(tensors, axis=axis)


# ==============================================================================
# ResNet18 路由器（3分类）
# ==============================================================================

def _basic_block(x, out_channels, stride, scope, is_training,
                 data_format='NCHW'):
    """
    ResNet BasicBlock: 2层 conv3x3 + BN + 残差连接。
    当通道数或步长改变时，使用 1x1 投影快捷连接。
    """
    with tf.compat.v1.variable_scope(scope):
        if data_format == 'NCHW':
            in_channels = x.get_shape().as_list()[1]
        else:
            in_channels = x.get_shape().as_list()[-1]

        # 第一层 conv3x3 -> BN -> ReLU
        h = _conv2d(x, out_channels, 3, stride, "conv1", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn1", data_format)
        h = tf.nn.relu(h)

        # 第二层 conv3x3 -> BN
        h = _conv2d(h, out_channels, 3, 1, "conv2", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn2", data_format)

        # 快捷连接
        if stride != 1 or in_channels != out_channels:
            shortcut = _conv2d(x, out_channels, 1, stride, "shortcut_conv",
                               data_format, use_bias=False)
            shortcut = _batch_norm(shortcut, is_training, "shortcut_bn",
                                   data_format)
        else:
            shortcut = x

        return tf.nn.relu(h + shortcut)


def _make_layer(x, out_channels, num_blocks, stride, scope, is_training,
                data_format='NCHW'):
    """构建 ResNet 的一个 stage（多个 BasicBlock）。"""
    with tf.compat.v1.variable_scope(scope):
        h = _basic_block(x, out_channels, stride, "block_0", is_training,
                         data_format)
        for i in range(1, num_blocks):
            h = _basic_block(h, out_channels, 1, f"block_{i}", is_training,
                             data_format)
        return h


def build_resnet18_router(image_input, config, is_training=False):
    """
    ResNet18 路由器：图像输入 -> 3分类。

    输入: [batch, 3, H, W] (NCHW)
    输出: logits [batch, 3], class_id (scalar int32)

    分类含义:
      0 = 跳过计算
      1 = 使用轻量 UNet 专家
      2 = 使用重量 UNet 专家
    """
    num_classes = config['num_classes']
    data_format = config['data_format']

    with tf.compat.v1.variable_scope("router_resnet18"):
        # conv1: 7x7, stride=2, 64 通道
        h = _conv2d(image_input, 64, 7, 2, "conv1", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn1", data_format)
        h = tf.nn.relu(h)

        # max pool: 3x3, stride=2
        h = _maxpool2d(h, 3, 2, data_format)

        # 4 个 stage
        h = _make_layer(h, 64, 2, 1, "layer1", is_training, data_format)
        h = _make_layer(h, 128, 2, 2, "layer2", is_training, data_format)
        h = _make_layer(h, 256, 2, 2, "layer3", is_training, data_format)
        h = _make_layer(h, 512, 2, 2, "layer4", is_training, data_format)

        # 全局平均池化 -> [batch, 512]
        h = _global_avg_pool(h, data_format)

        # 全连接分类层 -> [batch, num_classes]
        with tf.compat.v1.variable_scope("fc"):
            w = tf.compat.v1.get_variable(
                "weight", [512, num_classes],
                initializer=tf.compat.v1.initializers.glorot_uniform(),
            )
            b = tf.compat.v1.get_variable(
                "bias", [num_classes],
                initializer=tf.compat.v1.initializers.zeros(),
            )
            logits = tf.matmul(h, w) + b

        class_id = tf.cast(tf.argmax(logits, axis=1), tf.int32)

    return logits, class_id


# ==============================================================================
# UNet 专家（轻量 / 重量 两种配置）
# ==============================================================================

def _encoder_block(x, out_channels, scope, is_training, data_format='NCHW'):
    """UNet 编码器块: conv3x3 -> BN -> ReLU -> conv3x3 -> BN -> ReLU"""
    with tf.compat.v1.variable_scope(scope):
        h = _conv2d(x, out_channels, 3, 1, "conv1", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn1", data_format)
        h = tf.nn.relu(h)
        h = _conv2d(h, out_channels, 3, 1, "conv2", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn2", data_format)
        h = tf.nn.relu(h)
        return h


def _decoder_block(x, skip, out_channels, scope, is_training,
                   data_format='NCHW'):
    """
    UNet 解码器块:
      上采样 2x -> concat(skip) -> conv3x3 -> BN -> ReLU -> conv3x3 -> BN -> ReLU
    """
    with tf.compat.v1.variable_scope(scope):
        h = _upsample_nearest(x, 2, data_format)
        h = _concat([h, skip], data_format)
        h = _conv2d(h, out_channels, 3, 1, "conv1", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn1", data_format)
        h = tf.nn.relu(h)
        h = _conv2d(h, out_channels, 3, 1, "conv2", data_format,
                    use_bias=False)
        h = _batch_norm(h, is_training, "bn2", data_format)
        h = tf.nn.relu(h)
        return h


def build_unet(image_input, channels_list, bottleneck_ch, output_ch,
               scope, is_training, data_format='NCHW'):
    """
    UNet 编码-解码网络。

    Args:
        image_input: [batch, C, H, W] (NCHW)
        channels_list: 编码器各层通道数，如 [16,32,64,128] 或 [64,128,256,512]
        bottleneck_ch: 瓶颈层通道数
        output_ch: 输出通道数（分割掩码类别数）
        scope: 变量作用域名
        is_training: 是否训练模式
        data_format: 数据格式

    Returns:
        [batch, output_ch, H, W] 分割掩码（sigmoid 输出，值域 [0,1]）
    """
    with tf.compat.v1.variable_scope(scope):
        skips = []
        h = image_input

        # 编码器（下采样）
        for i, ch in enumerate(channels_list):
            h = _encoder_block(h, ch, f"enc_{i}", is_training, data_format)
            skips.append(h)
            h = _maxpool2d(h, 2, 2, data_format)

        # 瓶颈层
        h = _encoder_block(h, bottleneck_ch, "bottleneck", is_training,
                           data_format)

        # 解码器（上采样 + skip connection）
        for i, ch in enumerate(reversed(channels_list)):
            skip = skips[len(channels_list) - 1 - i]
            h = _decoder_block(h, skip, ch, f"dec_{i}", is_training,
                               data_format)

        # 最终 1x1 卷积 -> sigmoid
        h = _conv2d(h, output_ch, 1, 1, "final_conv", data_format,
                    use_bias=True)
        h = tf.nn.sigmoid(h)
        return h


# ==============================================================================
# 推理图：基于 tf.case 的条件专家执行
# ==============================================================================

def build_moe_resnet_unet_graph(image_input, config):
    """
    构建 MoE 推理计算图（含 tf.case 条件执行）。

    路由逻辑：
      - ResNet18 输出 class_id ∈ {0, 1, 2}
      - class_id == 0: 跳过计算，输出全零
      - class_id == 1: 轻量 UNet 专家
      - class_id == 2: 重量 UNet 专家

    Args:
        image_input: [batch, 3, H, W] placeholder
        config: MODEL_CONFIG dict

    Returns:
        output: [batch, output_ch, H, W] 分割掩码
        routing_class: scalar int32 路由类别
        router_logits: [batch, 3] 路由器分类 logits
    """
    batch_size = config['infer_batch_size']
    output_ch = config['unet_output_channels']
    H = config['image_shape'][2]
    W = config['image_shape'][3]
    data_format = config['data_format']

    with tf.compat.v1.variable_scope("moe"):
        # Step 1: ResNet18 路由器
        router_logits, class_id_batch = build_resnet18_router(
            image_input, config, is_training=False)

        # batch=1 时取标量
        class_id = class_id_batch[0]

        # Step 2: 条件判断
        is_class_0 = tf.equal(class_id, tf.constant(0, dtype=tf.int32))
        is_class_1 = tf.equal(class_id, tf.constant(1, dtype=tf.int32))

        # Step 3: 定义各分支执行函数
        def skip_fn():
            """类别 0: 跳过，返回全零"""
            return tf.zeros([batch_size, output_ch, H, W], dtype=tf.float32)

        def expert1_fn():
            """类别 1: 轻量 UNet 专家"""
            return build_unet(
                image_input,
                config['unet_light_channels'],
                config['unet_light_bottleneck'],
                output_ch,
                "expert_unet_light",
                is_training=False,
                data_format=data_format,
            )

        def expert2_fn():
            """类别 2: 重量 UNet 专家"""
            return build_unet(
                image_input,
                config['unet_heavy_channels'],
                config['unet_heavy_bottleneck'],
                output_ch,
                "expert_unet_heavy",
                is_training=False,
                data_format=data_format,
            )

        # Step 4: tf.case 条件执行（生成 Switch/Merge 节点）
        result = tf.case(
            [(is_class_0, skip_fn),
             (is_class_1, expert1_fn)],
            default=expert2_fn,
            name="moe_expert_select",
        )

        # 命名输出节点
        output = tf.identity(result, name="output")
        routing_class = tf.identity(class_id, name="routing_class")
        router_logits_out = tf.identity(router_logits, name="router_logits")

    return output, routing_class, router_logits_out


# ==============================================================================
# 训练图：所有专家均参与计算（用于梯度反传）
# ==============================================================================

def build_moe_resnet_unet_graph_train(image_input, config):
    """
    训练模式：所有专家均前向计算，通过 softmax 软权重加权组合。

    Args:
        image_input: [batch, 3, H, W] placeholder
        config: MODEL_CONFIG dict

    Returns:
        output: [batch, output_ch, H, W] 加权组合输出
        router_logits: [batch, 3] 路由器分类 logits
        router_probs: [batch, 3] 路由概率
    """
    output_ch = config['unet_output_channels']
    data_format = config['data_format']

    with tf.compat.v1.variable_scope("moe"):
        # Step 1: 路由器
        router_logits, _ = build_resnet18_router(
            image_input, config, is_training=True)
        router_probs = tf.nn.softmax(router_logits)  # [batch, 3]

        # Step 2: 所有专家均计算（梯度需要）
        # 类别 0 输出全零（跳过等价）
        img_shape = tf.shape(image_input)
        if data_format == 'NCHW':
            zeros_output = tf.zeros(
                [img_shape[0], output_ch, img_shape[2], img_shape[3]],
                dtype=tf.float32,
            )
        else:
            zeros_output = tf.zeros(
                [img_shape[0], img_shape[1], img_shape[2], output_ch],
                dtype=tf.float32,
            )

        light_output = build_unet(
            image_input,
            config['unet_light_channels'],
            config['unet_light_bottleneck'],
            output_ch,
            "expert_unet_light",
            is_training=True,
            data_format=data_format,
        )

        heavy_output = build_unet(
            image_input,
            config['unet_heavy_channels'],
            config['unet_heavy_bottleneck'],
            output_ch,
            "expert_unet_heavy",
            is_training=True,
            data_format=data_format,
        )

        # Step 3: 软权重加权组合
        # router_probs[:, 0] -> 跳过权重
        # router_probs[:, 1] -> 轻量 UNet 权重
        # router_probs[:, 2] -> 重量 UNet 权重
        if data_format == 'NCHW':
            w0 = tf.reshape(router_probs[:, 0], [-1, 1, 1, 1])
            w1 = tf.reshape(router_probs[:, 1], [-1, 1, 1, 1])
            w2 = tf.reshape(router_probs[:, 2], [-1, 1, 1, 1])
        else:
            w0 = tf.reshape(router_probs[:, 0], [-1, 1, 1, 1])
            w1 = tf.reshape(router_probs[:, 1], [-1, 1, 1, 1])
            w2 = tf.reshape(router_probs[:, 2], [-1, 1, 1, 1])

        combined = w0 * zeros_output + w1 * light_output + w2 * heavy_output

        output = tf.identity(combined, name="output")
        router_logits_out = tf.identity(router_logits, name="router_logits")
        router_probs_out = tf.identity(router_probs, name="router_probs")

    return output, router_logits_out, router_probs_out
