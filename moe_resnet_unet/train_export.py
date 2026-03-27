"""
MoE ResNet18-UNet 训练与导出脚本
1. 生成合成图像数据 (3类场景)
2. 训练 Gate(ResNet18) + Expert(UNet) 联合模型
3. 导出推理图为 frozen pb
"""
import os
import numpy as np
import tensorflow as tf

# 禁用 TF2 行为，使 tf.cond 生成 Switch/Merge 节点
tf.compat.v1.disable_v2_behavior()

from config import MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG
from model import build_moe_graph, build_moe_graph_train


def generate_synthetic_batch(batch_size, config):
    """
    生成合成图像数据:
    - Class 0 (跳过): 低纹理/简单图像 (接近纯色)
    - Class 1 (Expert1): 中等复杂度图像 (中等纹理)
    - Class 2 (Expert2): 高复杂度图像 (丰富纹理)

    返回: images [B,H,W,C], labels [B], targets [B,H,W,C]
    """
    h = config['image_height']
    w = config['image_width']
    c = config['image_channels']

    images = np.zeros((batch_size, h, w, c), dtype=np.float32)
    labels = np.zeros((batch_size,), dtype=np.int32)
    targets = np.zeros((batch_size, h, w, c), dtype=np.float32)

    for i in range(batch_size):
        cls = np.random.randint(0, 3)
        labels[i] = cls

        if cls == 0:
            # 简单图像: 纯色 + 轻微噪声 → 跳过处理 (target = input)
            base_color = np.random.uniform(0.3, 0.7, (1, 1, c)).astype(np.float32)
            images[i] = base_color + np.random.normal(0, 0.02, (h, w, c)).astype(np.float32)
            targets[i] = images[i]  # 跳过: 输出=输入
        elif cls == 1:
            # 中等复杂度: 渐变 + 中等噪声 → Expert1 轻度增强
            grad = np.linspace(0.2, 0.8, w).reshape(1, w, 1).astype(np.float32)
            images[i] = np.broadcast_to(grad, (h, w, c)).copy()
            images[i] += np.random.normal(0, 0.1, (h, w, c)).astype(np.float32)
            # target: 对比度增强
            targets[i] = np.clip(images[i] * 1.3 - 0.15, 0, 1).astype(np.float32)
        else:
            # 高复杂度: 随机纹理 → Expert2 深度处理
            images[i] = np.random.uniform(0, 1, (h, w, c)).astype(np.float32)
            # target: 平滑滤波效果 (简化)
            kernel_size = 5
            from scipy.ndimage import uniform_filter
            for ch in range(c):
                targets[i, :, :, ch] = uniform_filter(
                    images[i, :, :, ch], size=kernel_size)

    images = np.clip(images, 0, 1)
    targets = np.clip(targets, 0, 1)
    return images, labels, targets


def generate_synthetic_batch_simple(batch_size, config):
    """
    无 scipy 依赖的简单合成数据生成
    """
    h = config['image_height']
    w = config['image_width']
    c = config['image_channels']

    images = np.zeros((batch_size, h, w, c), dtype=np.float32)
    labels = np.zeros((batch_size,), dtype=np.int32)
    targets = np.zeros((batch_size, h, w, c), dtype=np.float32)

    for i in range(batch_size):
        cls = np.random.randint(0, 3)
        labels[i] = cls

        if cls == 0:
            # 简单图像 → 跳过
            base_color = np.random.uniform(0.3, 0.7, (1, 1, c)).astype(np.float32)
            images[i] = base_color + np.random.normal(0, 0.02, (h, w, c)).astype(np.float32)
            targets[i] = images[i]
        elif cls == 1:
            # 中等复杂度 → Expert1
            grad = np.linspace(0.2, 0.8, w).reshape(1, w, 1).astype(np.float32)
            images[i] = np.broadcast_to(grad, (h, w, c)).copy()
            images[i] += np.random.normal(0, 0.1, (h, w, c)).astype(np.float32)
            targets[i] = np.clip(images[i] * 1.3 - 0.15, 0, 1).astype(np.float32)
        else:
            # 高复杂度 → Expert2
            images[i] = np.random.uniform(0, 1, (h, w, c)).astype(np.float32)
            # 简单均值模糊替代 scipy
            targets[i] = images[i] * 0.7 + 0.15

    images = np.clip(images, 0, 1)
    targets = np.clip(targets, 0, 1)
    return images, labels, targets


def train(model_config, train_config):
    """训练 MoE 模型"""
    h = model_config['image_height']
    w = model_config['image_width']
    c = model_config['image_channels']
    num_classes = model_config['num_classes']
    bs = train_config['train_batch_size']

    tf.compat.v1.reset_default_graph()
    graph = tf.Graph()

    with graph.as_default():
        # 输入占位符
        input_ph = tf.compat.v1.placeholder(
            tf.float32, [None, h, w, c], name='input_image')
        label_ph = tf.compat.v1.placeholder(
            tf.int32, [None], name='label')
        target_ph = tf.compat.v1.placeholder(
            tf.float32, [None, h, w, c], name='target_image')

        # 构建训练图
        output, gate_logits, gate_probs = build_moe_graph_train(
            input_ph, model_config)

        # 损失函数
        # 1. Gate 分类损失
        gate_loss = tf.reduce_mean(
            tf.nn.sparse_softmax_cross_entropy_with_logits(
                labels=label_ph, logits=gate_logits))

        # 2. Expert 重建损失 (MSE)
        expert_loss = tf.reduce_mean(tf.square(output - target_ph))

        # 总损失
        total_loss = (train_config['gate_loss_weight'] * gate_loss +
                      train_config['expert_loss_weight'] * expert_loss)

        # 优化器
        optimizer = tf.compat.v1.train.AdamOptimizer(
            learning_rate=train_config['learning_rate'])
        train_op = optimizer.minimize(total_loss)

        # Gate 准确率
        gate_pred = tf.argmax(gate_probs, axis=-1, output_type=tf.int32)
        gate_acc = tf.reduce_mean(tf.cast(tf.equal(gate_pred, label_ph), tf.float32))

    # 训练
    print("=" * 60)
    print("开始训练 MoE ResNet18-UNet 模型")
    print(f"  Image size: {h}x{w}x{c}")
    print(f"  Expert1 (UNet-Light): base_filters={model_config['expert1_base_filters']}")
    print(f"  Expert2 (UNet-Heavy): base_filters={model_config['expert2_base_filters']}")
    print(f"  Training steps: {train_config['num_steps']}")
    print("=" * 60)

    with tf.compat.v1.Session(graph=graph) as sess:
        sess.run(tf.compat.v1.global_variables_initializer())

        for step in range(1, train_config['num_steps'] + 1):
            images, labels, targets = generate_synthetic_batch_simple(
                bs, model_config)

            _, loss_val, g_loss, e_loss, acc = sess.run(
                [train_op, total_loss, gate_loss, expert_loss, gate_acc],
                feed_dict={input_ph: images, label_ph: labels, target_ph: targets})

            if step % train_config['log_interval'] == 0 or step == 1:
                print(f"  Step {step:4d} | Loss: {loss_val:.4f} "
                      f"(gate: {g_loss:.4f}, expert: {e_loss:.4f}) "
                      f"| Gate Acc: {acc:.2%}")

        # 收集训练好的变量
        trained_vars = {}
        for var in tf.compat.v1.global_variables():
            if 'Adam' not in var.name and 'beta' not in var.name:
                trained_vars[var.name] = sess.run(var)

        print(f"\n训练完成! 共收集 {len(trained_vars)} 个变量")

    return trained_vars


def export_inference_pb(trained_vars, model_config, output_config):
    """导出推理 frozen pb"""
    h = model_config['image_height']
    w = model_config['image_width']
    c = model_config['image_channels']
    bs = model_config['infer_batch_size']

    tf.compat.v1.reset_default_graph()
    graph = tf.Graph()

    with graph.as_default():
        # 固定 batch size 的输入
        input_ph = tf.compat.v1.placeholder(
            tf.float32, [bs, h, w, c], name='input_image')

        # 构建推理图 (带 tf.cond)
        output, gate_class, gate_logits, gate_probs = build_moe_graph(
            input_ph, model_config)

    # 加载权重并导出
    with tf.compat.v1.Session(graph=graph) as sess:
        sess.run(tf.compat.v1.global_variables_initializer())

        # 加载训练好的权重
        loaded = 0
        for var in tf.compat.v1.global_variables():
            if var.name in trained_vars:
                sess.run(var.assign(trained_vars[var.name]))
                loaded += 1
        print(f"\n加载 {loaded}/{len(tf.compat.v1.global_variables())} 个变量到推理图")

        # 验证推理
        test_input = np.random.uniform(0, 1, (bs, h, w, c)).astype(np.float32)
        out_val, cls_val = sess.run(
            [output, gate_class], feed_dict={input_ph: test_input})
        print(f"推理验证:")
        print(f"  输出 shape: {out_val.shape}")
        print(f"  Gate 分类: {cls_val}")
        class_names = {0: '跳过', 1: 'Expert1(UNet-Light)', 2: 'Expert2(UNet-Heavy)'}
        print(f"  路由决策: {class_names.get(cls_val[0], 'unknown')}")

        # 冻结图
        output_nodes = [n.split('/')[-1] if '/' not in n else n
                        for n in output_config['output_nodes']]
        frozen_graph = tf.compat.v1.graph_util.convert_variables_to_constants(
            sess, graph.as_graph_def(), output_config['output_nodes'])

        # 保存
        os.makedirs(os.path.dirname(output_config['pb_path']), exist_ok=True)
        with open(output_config['pb_path'], 'wb') as f:
            f.write(frozen_graph.SerializeToString())

        pb_size = os.path.getsize(output_config['pb_path'])
        print(f"\n已导出 frozen pb:")
        print(f"  路径: {output_config['pb_path']}")
        print(f"  大小: {pb_size / 1024 / 1024:.2f} MB")
        print(f"  输入节点: {output_config['input_node']}")
        print(f"  输出节点: {output_config['output_nodes']}")

        # 统计 Switch/Merge 节点
        switch_count = sum(1 for n in frozen_graph.node if n.op == 'Switch')
        merge_count = sum(1 for n in frozen_graph.node if n.op == 'Merge')
        print(f"  tf.cond 节点: Switch={switch_count}, Merge={merge_count}")

        print(f"\nATC 编译命令:")
        print(f"  atc --model={output_config['pb_path']} "
              f"--framework=3 "
              f"--output=moe_resnet_unet "
              f"--soc_version=Ascend310B4 "
              f"--input_shape=\"{output_config['input_node']}:"
              f"{bs},{h},{w},{c}\"")

    return frozen_graph


if __name__ == '__main__':
    print("MoE ResNet18(Gate) + UNet(Experts) 模型")
    print("  Class 0: 跳过计算")
    print("  Class 1: Expert1 (UNet-Light)")
    print("  Class 2: Expert2 (UNet-Heavy)")
    print()

    # 训练
    trained_vars = train(MODEL_CONFIG, TRAIN_CONFIG)

    # 导出
    frozen_graph = export_inference_pb(trained_vars, MODEL_CONFIG, OUTPUT_CONFIG)

    print("\n完成!")
