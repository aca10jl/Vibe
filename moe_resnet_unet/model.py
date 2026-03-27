"""
MoE 组合模型: ResNet18 Gate + UNet Experts
- Gate (ResNet18): 3分类 → 0=跳过计算, 1=Expert1, 2=Expert2
- Expert1: UNet-Light (较少通道)
- Expert2: UNet-Heavy (较多通道)
- 使用 tf.cond 实现真正的稀疏条件执行
"""
import tensorflow as tf


# ============================================================
# ResNet18 Gate Network
# ============================================================

def _conv_bn_relu(inputs, filters, kernel_size, strides, scope, is_training=False):
    """Conv2D + BatchNorm + ReLU 基础模块"""
    with tf.compat.v1.variable_scope(scope):
        conv = tf.compat.v1.layers.conv2d(
            inputs, filters, kernel_size, strides=strides,
            padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv')
        # 推理时使用固定的 BN 参数
        bn = tf.compat.v1.layers.batch_normalization(
            conv, training=is_training, name='bn')
        return tf.nn.relu(bn)


def _resnet_basic_block(inputs, filters, strides, scope, is_training=False):
    """ResNet BasicBlock: 2个 3x3 conv + shortcut"""
    with tf.compat.v1.variable_scope(scope):
        # 主路径
        x = tf.compat.v1.layers.conv2d(
            inputs, filters, 3, strides=strides, padding='same',
            use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv1')
        x = tf.compat.v1.layers.batch_normalization(
            x, training=is_training, name='bn1')
        x = tf.nn.relu(x)

        x = tf.compat.v1.layers.conv2d(
            x, filters, 3, strides=1, padding='same',
            use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv2')
        x = tf.compat.v1.layers.batch_normalization(
            x, training=is_training, name='bn2')

        # shortcut
        if strides != 1 or inputs.get_shape()[-1] != filters:
            shortcut = tf.compat.v1.layers.conv2d(
                inputs, filters, 1, strides=strides, padding='same',
                use_bias=False,
                kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
                name='shortcut_conv')
            shortcut = tf.compat.v1.layers.batch_normalization(
                shortcut, training=is_training, name='shortcut_bn')
        else:
            shortcut = inputs

        return tf.nn.relu(x + shortcut)


def build_resnet18_gate(inputs, num_classes, scope='gate', is_training=False):
    """
    ResNet18 门控网络
    输入: [batch, H, W, 3]
    输出: [batch, num_classes] 的 softmax 概率
    """
    with tf.compat.v1.variable_scope(scope):
        # 初始卷积: 7x7, stride 2, 64 filters
        x = _conv_bn_relu(inputs, 64, 7, 2, 'conv1', is_training)
        # MaxPool: 3x3, stride 2
        x = tf.compat.v1.layers.max_pooling2d(x, 3, 2, padding='same', name='pool1')

        # Layer1: 2 blocks, 64 filters, stride 1
        x = _resnet_basic_block(x, 64, 1, 'layer1_block1', is_training)
        x = _resnet_basic_block(x, 64, 1, 'layer1_block2', is_training)

        # Layer2: 2 blocks, 128 filters, stride 2
        x = _resnet_basic_block(x, 128, 2, 'layer2_block1', is_training)
        x = _resnet_basic_block(x, 128, 1, 'layer2_block2', is_training)

        # Layer3: 2 blocks, 256 filters, stride 2
        x = _resnet_basic_block(x, 256, 2, 'layer3_block1', is_training)
        x = _resnet_basic_block(x, 256, 1, 'layer3_block2', is_training)

        # Layer4: 2 blocks, 512 filters, stride 2
        x = _resnet_basic_block(x, 512, 2, 'layer4_block1', is_training)
        x = _resnet_basic_block(x, 512, 1, 'layer4_block2', is_training)

        # Global Average Pooling
        x = tf.reduce_mean(x, axis=[1, 2], name='global_avg_pool')

        # 分类头
        logits = tf.compat.v1.layers.dense(
            x, num_classes,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='fc')
        probs = tf.nn.softmax(logits, name='probs')

    return logits, probs


# ============================================================
# UNet Expert Networks
# ============================================================

def _unet_encoder_block(inputs, filters, scope, is_training=False):
    """UNet encoder block: 2x Conv3x3+BN+ReLU → MaxPool"""
    with tf.compat.v1.variable_scope(scope):
        x = tf.compat.v1.layers.conv2d(
            inputs, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv1')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn1')
        x = tf.nn.relu(x)

        x = tf.compat.v1.layers.conv2d(
            x, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv2')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn2')
        x = tf.nn.relu(x)

        pool = tf.compat.v1.layers.max_pooling2d(x, 2, 2, padding='same', name='pool')
        return x, pool  # skip connection, downsampled


def _unet_bottleneck(inputs, filters, scope, is_training=False):
    """UNet bottleneck: 2x Conv3x3+BN+ReLU"""
    with tf.compat.v1.variable_scope(scope):
        x = tf.compat.v1.layers.conv2d(
            inputs, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv1')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn1')
        x = tf.nn.relu(x)

        x = tf.compat.v1.layers.conv2d(
            x, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv2')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn2')
        x = tf.nn.relu(x)
        return x


def _unet_decoder_block(inputs, skip, filters, scope, is_training=False):
    """UNet decoder block: Upsample → Concat(skip) → 2x Conv3x3+BN+ReLU"""
    with tf.compat.v1.variable_scope(scope):
        # 转置卷积上采样
        x = tf.compat.v1.layers.conv2d_transpose(
            inputs, filters, 2, strides=2, padding='same',
            use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='upconv')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='upbn')
        x = tf.nn.relu(x)

        # 拼接 skip connection
        x = tf.concat([x, skip], axis=-1, name='concat')

        x = tf.compat.v1.layers.conv2d(
            x, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv1')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn1')
        x = tf.nn.relu(x)

        x = tf.compat.v1.layers.conv2d(
            x, filters, 3, padding='same', use_bias=False,
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='conv2')
        x = tf.compat.v1.layers.batch_normalization(x, training=is_training, name='bn2')
        x = tf.nn.relu(x)
        return x


def build_unet(inputs, base_filters, depth, output_channels, scope, is_training=False):
    """
    构建 UNet 网络
    Args:
        inputs: [batch, H, W, C] 输入图像
        base_filters: 基础通道数，逐层翻倍
        depth: encoder/decoder 深度
        output_channels: 输出通道数
        scope: 变量作用域
    Returns:
        output: [batch, H, W, output_channels]
    """
    with tf.compat.v1.variable_scope(scope):
        skips = []
        x = inputs

        # Encoder
        for i in range(depth):
            filters = base_filters * (2 ** i)
            skip, x = _unet_encoder_block(x, filters, f'enc_{i}', is_training)
            skips.append(skip)

        # Bottleneck
        bottleneck_filters = base_filters * (2 ** depth)
        x = _unet_bottleneck(x, bottleneck_filters, 'bottleneck', is_training)

        # Decoder
        for i in range(depth - 1, -1, -1):
            filters = base_filters * (2 ** i)
            x = _unet_decoder_block(x, skips[i], filters, f'dec_{i}', is_training)

        # 输出层: 1x1 conv
        output = tf.compat.v1.layers.conv2d(
            x, output_channels, 1, padding='same',
            kernel_initializer=tf.compat.v1.glorot_uniform_initializer(),
            name='output_conv')

    return output


# ============================================================
# MoE 组合: tf.cond 条件执行
# ============================================================

def _cond_expert(inputs, expert_id, gate_class, config, scope_suffix, is_training=False):
    """
    条件执行专家网络
    当 gate_class == expert_id 时执行对应 UNet，否则返回零张量
    """
    batch_size = config['infer_batch_size']
    h = config['image_height']
    w = config['image_width']
    out_c = config['output_channels']

    is_selected = tf.equal(gate_class, expert_id, name=f'is_expert{scope_suffix}')
    # gate_class 是 scalar (batch=1)，squeeze 到标量
    is_selected_scalar = tf.squeeze(is_selected)

    if expert_id == 1:
        base_filters = config['expert1_base_filters']
        depth = config['expert1_depth']
        expert_scope = 'expert1_unet'
    else:
        base_filters = config['expert2_base_filters']
        depth = config['expert2_depth']
        expert_scope = 'expert2_unet'

    def true_fn():
        return build_unet(inputs, base_filters, depth, out_c,
                          expert_scope, is_training)

    def false_fn():
        return tf.zeros([batch_size, h, w, out_c], dtype=tf.float32)

    return tf.cond(is_selected_scalar, true_fn, false_fn,
                   name=f'cond_expert{scope_suffix}')


def build_moe_graph(inputs, config):
    """
    构建推理 MoE 图 (使用 tf.cond)
    流程:
        1. ResNet18 Gate → 分类 (0/1/2)
        2. tf.cond: class==0 → 跳过, class==1 → Expert1, class==2 → Expert2
        3. 输出 = Expert1结果 + Expert2结果 (互斥，只有一个非零)
    """
    with tf.compat.v1.variable_scope('moe'):
        # Gate: ResNet18
        gate_logits, gate_probs = build_resnet18_gate(
            inputs, config['num_classes'], 'gate')

        # 取 argmax 作为路由决策
        gate_class = tf.argmax(gate_probs, axis=-1, output_type=tf.int32,
                               name='gate_argmax')  # [batch]

        # 条件执行 Expert1 (class==1)
        expert1_out = _cond_expert(inputs, 1, gate_class, config, '1')

        # 条件执行 Expert2 (class==2)
        expert2_out = _cond_expert(inputs, 2, gate_class, config, '2')

        # class==0 时两个 expert 都返回 zero，输出也是 zero (跳过计算)
        output = tf.add(expert1_out, expert2_out, name='output')

        # 输出 gate 类别信息
        gate_class_out = tf.identity(gate_class, name='gate_class')

    return output, gate_class_out, gate_logits, gate_probs


def build_moe_graph_train(inputs, config):
    """
    构建训练 MoE 图 (不使用 tf.cond，所有专家都参与前向传播)
    使用 soft routing 权重来加权专家输出，允许梯度流向所有专家
    """
    with tf.compat.v1.variable_scope('moe'):
        # Gate: ResNet18
        gate_logits, gate_probs = build_resnet18_gate(
            inputs, config['num_classes'], 'gate', is_training=True)

        # 构建两个 UNet 专家 (都执行前向传播)
        expert1_out = build_unet(
            inputs,
            config['expert1_base_filters'],
            config['expert1_depth'],
            config['output_channels'],
            'expert1_unet',
            is_training=True)

        expert2_out = build_unet(
            inputs,
            config['expert2_base_filters'],
            config['expert2_depth'],
            config['output_channels'],
            'expert2_unet',
            is_training=True)

        # 使用 soft routing 权重
        # gate_probs: [batch, 3] → 取 class 1 和 class 2 的概率作为权重
        w_skip = gate_probs[:, 0:1]   # [batch, 1]
        w_exp1 = gate_probs[:, 1:2]   # [batch, 1]
        w_exp2 = gate_probs[:, 2:3]   # [batch, 1]

        # 扩展到 [batch, 1, 1, 1] 以广播到 [batch, H, W, C]
        w_exp1_4d = tf.reshape(w_exp1, [-1, 1, 1, 1])
        w_exp2_4d = tf.reshape(w_exp2, [-1, 1, 1, 1])

        # 加权输出: skip 的权重不产生输出 (零向量)
        output = w_exp1_4d * expert1_out + w_exp2_4d * expert2_out

    return output, gate_logits, gate_probs
