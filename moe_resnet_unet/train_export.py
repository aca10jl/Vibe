# ==============================================================================
# MoE ResNet18 + UNet 模型训练 + 冻结 pb 导出
#
# 训练流程：
#   1. 生成合成数据（3类：空白/简单形状/复杂场景）
#   2. 训练路由器（ResNet18 分类）+ 专家（UNet 分割）
#   3. 导出推理图（含 tf.case 条件执行）为 frozen pb
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from config import MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG
from model import (build_moe_resnet_unet_graph,
                   build_moe_resnet_unet_graph_train)


# ==============================================================================
# 合成数据生成
# ==============================================================================

def _draw_circle(mask, cy, cx, radius, H, W):
    """在 mask 上画圆。"""
    yy, xx = np.ogrid[:H, :W]
    circle = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    mask[circle] = 1.0


def _draw_rectangle(mask, y0, x0, y1, x1):
    """在 mask 上画矩形。"""
    mask[y0:y1, x0:x1] = 1.0


def generate_synthetic_batch(batch_size, config):
    """
    生成合成训练数据。

    类别 0 (跳过): 低噪声均匀图像，掩码全零
    类别 1 (轻量专家): 单个简单几何形状，掩码为形状区域
    类别 2 (重量专家): 多个叠加形状+噪声背景，掩码为全部形状区域

    Returns:
        images: [batch, C, H, W] float32
        masks:  [batch, 1, H, W] float32
        labels: [batch] int32 路由标签
    """
    C = config['image_shape'][1]
    H = config['image_shape'][2]
    W = config['image_shape'][3]

    images = np.zeros((batch_size, C, H, W), dtype=np.float32)
    masks = np.zeros((batch_size, 1, H, W), dtype=np.float32)
    labels = np.random.randint(0, config['num_classes'], size=batch_size)

    for i in range(batch_size):
        if labels[i] == 0:
            # 类别 0: 低噪声空白图像 -> 跳过
            images[i] = np.random.rand(C, H, W).astype(np.float32) * 0.05
            masks[i] = 0.0

        elif labels[i] == 1:
            # 类别 1: 单个简单形状 -> 轻量 UNet
            bg = np.random.rand(C, H, W).astype(np.float32) * 0.2
            m = np.zeros((H, W), dtype=np.float32)

            shape_type = np.random.randint(0, 2)
            if shape_type == 0:
                # 圆形
                cy = np.random.randint(H // 4, 3 * H // 4)
                cx = np.random.randint(W // 4, 3 * W // 4)
                radius = np.random.randint(H // 8, H // 4)
                _draw_circle(m, cy, cx, radius, H, W)
            else:
                # 矩形
                y0 = np.random.randint(0, H // 2)
                x0 = np.random.randint(0, W // 2)
                y1 = np.random.randint(y0 + H // 6, min(y0 + H // 2, H))
                x1 = np.random.randint(x0 + W // 6, min(x0 + W // 2, W))
                _draw_rectangle(m, y0, x0, y1, x1)

            # 形状区域在图像上有高亮
            for c in range(C):
                bg[c] += m * (0.5 + 0.5 * np.random.rand())
            images[i] = np.clip(bg, 0, 1)
            masks[i, 0] = m

        else:
            # 类别 2: 复杂场景（多个形状+噪声）-> 重量 UNet
            bg = np.random.rand(C, H, W).astype(np.float32) * 0.4
            bg += np.random.randn(C, H, W).astype(np.float32) * 0.1
            m = np.zeros((H, W), dtype=np.float32)

            num_shapes = np.random.randint(3, 7)
            for _ in range(num_shapes):
                shape_type = np.random.randint(0, 2)
                if shape_type == 0:
                    cy = np.random.randint(0, H)
                    cx = np.random.randint(0, W)
                    radius = np.random.randint(H // 16, H // 4)
                    _draw_circle(m, cy, cx, radius, H, W)
                else:
                    y0 = np.random.randint(0, H - 10)
                    x0 = np.random.randint(0, W - 10)
                    y1 = min(y0 + np.random.randint(10, H // 3), H)
                    x1 = min(x0 + np.random.randint(10, W // 3), W)
                    _draw_rectangle(m, y0, x0, y1, x1)

            for c in range(C):
                bg[c] += m * (0.3 + 0.4 * np.random.rand())
            images[i] = np.clip(bg, 0, 1)
            masks[i, 0] = m

    return images, masks, labels.astype(np.int32)


# ==============================================================================
# 损失函数
# ==============================================================================

def load_balancing_loss(router_probs, num_classes):
    """负载均衡辅助损失，防止路由崩溃。"""
    mean_probs = tf.reduce_mean(router_probs, axis=0)
    return tf.cast(num_classes, tf.float32) * tf.reduce_sum(mean_probs * mean_probs)


# ==============================================================================
# 训练
# ==============================================================================

def train(model_config, train_config):
    """训练阶段：路由器分类 + 专家分割联合训练。"""
    img_shape = model_config['image_shape']

    print("=" * 60)
    print("MoE ResNet18 + UNet 模型训练")
    print("=" * 60)
    print(f"  路由器:       ResNet18 ({model_config['num_classes']}分类)")
    print(f"  Expert1:      轻量 UNet {model_config['unet_light_channels']}")
    print(f"  Expert2:      重量 UNet {model_config['unet_heavy_channels']}")
    print(f"  输入形状:     {img_shape}")
    print()

    train_graph = tf.compat.v1.Graph()
    with train_graph.as_default():
        images_ph = tf.compat.v1.placeholder(
            tf.float32,
            [None, img_shape[1], img_shape[2], img_shape[3]],
            name="input_image",
        )
        masks_ph = tf.compat.v1.placeholder(
            tf.float32,
            [None, model_config['unet_output_channels'],
             img_shape[2], img_shape[3]],
            name="target_mask",
        )
        labels_ph = tf.compat.v1.placeholder(
            tf.int32, [None], name="route_labels")

        output, router_logits, router_probs = \
            build_moe_resnet_unet_graph_train(images_ph, model_config)

        # 路由器分类损失
        router_loss = tf.reduce_mean(
            tf.nn.sparse_softmax_cross_entropy_with_logits(
                labels=labels_ph, logits=router_logits))

        # 专家分割损失（MSE）
        expert_loss = tf.reduce_mean(tf.square(output - masks_ph))

        # 负载均衡损失
        lb_loss = load_balancing_loss(router_probs,
                                      model_config['num_classes'])

        total_loss = (train_config['router_loss_weight'] * router_loss
                      + train_config['expert_loss_weight'] * expert_loss
                      + train_config['lb_loss_weight'] * lb_loss)

        optimizer = tf.compat.v1.train.AdamOptimizer(
            train_config['learning_rate'])
        train_op = optimizer.minimize(total_loss)
        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=train_graph)
    sess.run(init_op)

    print("[Train] 开始训练 ...")
    for step in range(1, train_config['num_steps'] + 1):
        X_batch, M_batch, L_batch = generate_synthetic_batch(
            train_config['train_batch_size'], model_config)

        _, loss_val, r_loss, e_loss, lb_l, r_logits = sess.run(
            [train_op, total_loss, router_loss, expert_loss, lb_loss,
             router_logits],
            feed_dict={
                images_ph: X_batch,
                masks_ph: M_batch,
                labels_ph: L_batch,
            },
        )

        if step % train_config['log_interval'] == 0 or step == 1:
            # 路由分布统计
            preds = np.argmax(r_logits, axis=1)
            counts = np.bincount(preds, minlength=model_config['num_classes'])
            util = counts / len(preds)
            util_str = " ".join(
                f"C{i}:{u:.2f}" for i, u in enumerate(util))
            print(f"  Step {step:>4d}/{train_config['num_steps']} | "
                  f"loss={loss_val:.4f} router={r_loss:.4f} "
                  f"expert={e_loss:.4f} lb={lb_l:.4f} | {util_str}")

    print("[Train] 训练完成。\n")

    # 提取训练好的变量值
    trained_vars = {}
    for var in train_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        name = var.name
        if 'Adam' in name or 'beta1_power' in name or 'beta2_power' in name:
            continue
        trained_vars[name] = sess.run(var)
    sess.close()
    return trained_vars


# ==============================================================================
# 导出推理 pb
# ==============================================================================

def export_inference_pb(trained_vars, model_config, output_config):
    """构建推理图（含 tf.case），加载训练权重，冻结导出。"""
    img_shape = model_config['image_shape']

    print("=" * 60)
    print("构建推理图并导出 frozen pb")
    print("=" * 60)

    infer_graph = tf.compat.v1.Graph()
    with infer_graph.as_default():
        images_ph = tf.compat.v1.placeholder(
            tf.float32,
            [model_config['infer_batch_size'], img_shape[1],
             img_shape[2], img_shape[3]],
            name="input_image",
        )

        output, routing_class, router_logits = \
            build_moe_resnet_unet_graph(images_ph, model_config)

        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=infer_graph)
    sess.run(init_op)

    # 加载训练权重
    print("[Export] 加载训练权重到推理图 ...")
    loaded = 0
    for var in infer_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        if var.name in trained_vars:
            sess.run(var.assign(trained_vars[var.name]))
            loaded += 1
    print(f"[Export] 已加载 {loaded} 个变量。")

    # 验证推理
    print("[Export] 验证推理图 ...")
    test_input = np.random.randn(
        model_config['infer_batch_size'], img_shape[1],
        img_shape[2], img_shape[3]).astype(np.float32) * 0.1
    out_val, cls_val, logits_val = sess.run(
        [output, routing_class, router_logits],
        feed_dict={images_ph: test_input},
    )
    print(f"  输出 shape:   {out_val.shape}")
    print(f"  路由类别:     {cls_val}")
    print(f"  路由 logits:  {np.round(logits_val, 4)}")

    # 冻结导出
    pb_path = output_config['pb_path']
    output_node_names = output_config['output_nodes']

    graph_def = infer_graph.as_graph_def()
    frozen_def = tf.compat.v1.graph_util.convert_variables_to_constants(
        sess, graph_def, output_node_names)

    os.makedirs(os.path.dirname(pb_path) if os.path.dirname(pb_path) else '.',
                exist_ok=True)
    with open(pb_path, 'wb') as f:
        f.write(frozen_def.SerializeToString())

    size_kb = os.path.getsize(pb_path) / 1024
    print(f"\n[Export] frozen pb 已保存: {pb_path} ({size_kb:.1f} KB)")
    print(f"[Export] 冻结后节点数: {len(frozen_def.node)}")

    # ATC 编译参考
    bs = model_config['infer_batch_size']
    C, H, W = img_shape[1], img_shape[2], img_shape[3]
    print(f"\n[ATC 编译命令参考]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    print(f"  --input_shape=\"{output_config['input_node']}:"
          f"{bs},{C},{H},{W}\" \\")
    print(f"  --input_format=NCHW \\")
    print(f"  --output_type=FP32 \\")
    out_str = ";".join(output_config['output_nodes'])
    print(f"  --out_nodes=\"{out_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")

    sess.close()
    return pb_path


# ==============================================================================
# 主入口
# ==============================================================================

if __name__ == "__main__":
    print(f"[专家配置]")
    print(f"  路由器: ResNet18 ({MODEL_CONFIG['num_classes']}分类)")
    print(f"  Expert1 (轻量 UNet): channels={MODEL_CONFIG['unet_light_channels']}, "
          f"bottleneck={MODEL_CONFIG['unet_light_bottleneck']}")
    print(f"  Expert2 (重量 UNet): channels={MODEL_CONFIG['unet_heavy_channels']}, "
          f"bottleneck={MODEL_CONFIG['unet_heavy_bottleneck']}")
    print()

    trained_vars = train(MODEL_CONFIG, TRAIN_CONFIG)
    pb_path = export_inference_pb(trained_vars, MODEL_CONFIG, OUTPUT_CONFIG)
    print(f"\n[Done] pb 文件: {pb_path}")
    print("运行 python verify_pb.py 验证模型。")
