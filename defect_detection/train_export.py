# ==============================================================================
# 缺陷检测模型训练 + 冻结 pb 导出
#
# 两阶段训练：
#   Phase 1: 训练 UNet（主模型），用合成数据 + heatmap 标签
#   Phase 2: 训练 ResNet（子模型），用 UNet 输出 + cell 标签
#   导出：构建推理图（含 tf.cond）→ 加载权重 → 冻结 → 写 pb
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from config import DEFECT_MODEL_CONFIG, DEFECT_TRAIN_CONFIG, DEFECT_OUTPUT_CONFIG
from model import (build_defect_detection_graph,
                   build_unet_train_graph,
                   build_resnet_train_graph)


# ==============================================================================
# 合成数据生成
# ==============================================================================

def generate_synthetic_defect_data(batch_size, config):
    """
    生成合成训练数据。

    Returns:
        test_images:   [batch, 1, 448, 448] uint8
        ref_images:    [batch, 1, 448, 448] uint8
        gt_heatmaps:   [batch, 1, 448, 448] float32
        gt_cell_labels: [batch, 16] float32
    """
    H = config['image_height']
    W = config['image_width']
    grid_rows = config['grid_rows']
    grid_cols = config['grid_cols']
    patch_h = H // grid_rows
    patch_w = W // grid_cols

    # 参考图：随机噪声
    ref_images = np.random.randint(50, 200, (batch_size, 1, H, W),
                                    dtype=np.uint8)

    # 待检测图：参考图 + 随机缺陷
    test_images = ref_images.copy()
    gt_heatmaps = np.zeros((batch_size, 1, H, W), dtype=np.float32)
    gt_cell_labels = np.zeros((batch_size, grid_rows * grid_cols),
                               dtype=np.float32)

    for b in range(batch_size):
        # 随机放置 1-3 个缺陷
        num_defects = np.random.randint(1, 4)
        for _ in range(num_defects):
            # 缺陷中心位置
            cy = np.random.randint(20, H - 20)
            cx = np.random.randint(20, W - 20)
            # 缺陷大小
            radius = np.random.randint(10, 40)

            # 在待检测图上添加缺陷（亮斑或暗斑）
            y_lo = max(0, cy - radius)
            y_hi = min(H, cy + radius)
            x_lo = max(0, cx - radius)
            x_hi = min(W, cx + radius)

            defect_val = np.random.randint(0, 50) if np.random.rand() > 0.5 else \
                np.random.randint(200, 256)
            test_images[b, 0, y_lo:y_hi, x_lo:x_hi] = defect_val

            # 生成高斯 heatmap 标签
            yy, xx = np.meshgrid(np.arange(H), np.arange(W), indexing='ij')
            gaussian = np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) /
                              (2 * radius ** 2))
            gt_heatmaps[b, 0] = np.maximum(gt_heatmaps[b, 0], gaussian)

            # 标记 cell labels
            cell_row = min(cy // patch_h, grid_rows - 1)
            cell_col = min(cx // patch_w, grid_cols - 1)
            gt_cell_labels[b, cell_row * grid_cols + cell_col] = 1.0

    gt_heatmaps = np.clip(gt_heatmaps, 0.0, 1.0)

    return test_images, ref_images, gt_heatmaps, gt_cell_labels


# ==============================================================================
# Phase 1: 训练 UNet
# ==============================================================================

def train_unet(config, train_config):
    """训练 UNet 主模型，返回训练好的变量字典。"""
    batch_size = train_config['train_batch_size']

    print("=" * 60)
    print("Phase 1: 训练 UNet 主模型")
    print("=" * 60)

    train_graph = tf.compat.v1.Graph()
    with train_graph.as_default():
        graph_dict = build_unet_train_graph(config, batch_size=batch_size)

        optimizer = tf.compat.v1.train.AdamOptimizer(
            train_config['learning_rate'])
        train_op = optimizer.minimize(graph_dict['loss'])
        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=train_graph)
    sess.run(init_op)

    num_steps = train_config['num_steps_unet']
    log_interval = train_config['log_interval']

    print(f"  训练步数: {num_steps}")
    print(f"  Batch 大小: {batch_size}")
    print()

    for step in range(1, num_steps + 1):
        test_imgs, ref_imgs, gt_hmaps, _ = generate_synthetic_defect_data(
            batch_size, config)

        _, loss_val = sess.run(
            [train_op, graph_dict['loss']],
            feed_dict={
                graph_dict['test_image']: test_imgs,
                graph_dict['ref_image']: ref_imgs,
                graph_dict['gt_heatmap']: gt_hmaps,
            })

        if step % log_interval == 0 or step == 1:
            print(f"  Step {step:>5d}/{num_steps} | loss={loss_val:.4f}")

    print("[Phase 1] UNet 训练完成。\n")

    # 提取训练好的变量
    trained_vars = {}
    for var in train_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        name = var.name
        if 'Adam' in name or 'beta1_power' in name or 'beta2_power' in name:
            continue
        trained_vars[name] = sess.run(var)

    sess.close()
    return trained_vars


# ==============================================================================
# Phase 2: 训练 ResNet
# ==============================================================================

def train_resnet(config, train_config):
    """训练 ResNet 子模型，返回训练好的变量字典。"""
    batch_size = train_config['train_batch_size']

    print("=" * 60)
    print("Phase 2: 训练 ResNet 分类器")
    print("=" * 60)

    train_graph = tf.compat.v1.Graph()
    with train_graph.as_default():
        graph_dict = build_resnet_train_graph(config, batch_size=batch_size)

        # 只训练 ResNet 相关变量
        resnet_vars = [v for v in tf.compat.v1.trainable_variables()
                       if 'shared_resnet' in v.name]
        print(f"  ResNet 可训练参数: {len(resnet_vars)} 个变量")

        optimizer = tf.compat.v1.train.AdamOptimizer(
            train_config['learning_rate'])
        train_op = optimizer.minimize(graph_dict['loss'], var_list=resnet_vars)
        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=train_graph)
    sess.run(init_op)

    num_steps = train_config['num_steps_resnet']
    log_interval = train_config['log_interval']

    print(f"  训练步数: {num_steps}")
    print(f"  Batch 大小: {batch_size}")
    print()

    for step in range(1, num_steps + 1):
        test_imgs, ref_imgs, gt_hmaps, gt_cells = \
            generate_synthetic_defect_data(batch_size, config)

        _, loss_val = sess.run(
            [train_op, graph_dict['loss']],
            feed_dict={
                graph_dict['test_image']: test_imgs,
                graph_dict['ref_image']: ref_imgs,
                graph_dict['heatmap_input']: gt_hmaps,
                graph_dict['gt_cell_labels']: gt_cells,
            })

        if step % log_interval == 0 or step == 1:
            print(f"  Step {step:>5d}/{num_steps} | loss={loss_val:.4f}")

    print("[Phase 2] ResNet 训练完成。\n")

    # 提取训练好的变量
    trained_vars = {}
    for var in train_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        name = var.name
        if 'Adam' in name or 'beta1_power' in name or 'beta2_power' in name:
            continue
        trained_vars[name] = sess.run(var)

    sess.close()
    return trained_vars


# ==============================================================================
# 导出推理图
# ==============================================================================

def export_inference_pb(unet_vars, resnet_vars, config, output_config):
    """
    构建推理图（含 tf.cond），加载训练权重，冻结导出。

    Args:
        unet_vars: UNet 训练好的变量字典
        resnet_vars: ResNet 训练好的变量字典
        config: DEFECT_MODEL_CONFIG
        output_config: DEFECT_OUTPUT_CONFIG

    Returns:
        pb_path: 导出的 pb 文件路径
    """
    print("=" * 60)
    print("构建推理图并导出 frozen pb")
    print("=" * 60)

    infer_graph = tf.compat.v1.Graph()
    with infer_graph.as_default():
        graph_dict = build_defect_detection_graph(config)
        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=infer_graph)
    sess.run(init_op)

    # 加载训练权重
    print("[Export] 加载训练权重到推理图 ...")
    loaded = 0
    all_trained_vars = {}
    all_trained_vars.update(unet_vars)
    all_trained_vars.update(resnet_vars)

    for var in infer_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        if var.name in all_trained_vars:
            sess.run(var.assign(all_trained_vars[var.name]))
            loaded += 1
    print(f"[Export] 已加载 {loaded} 个变量。")

    # 验证推理
    print("[Export] 验证推理图 ...")
    H = config['image_height']
    W = config['image_width']
    test_img = np.random.randint(0, 256, (1, 1, H, W), dtype=np.uint8)
    ref_img = np.random.randint(0, 256, (1, 1, H, W), dtype=np.uint8)

    raw_out, refined_out = sess.run(
        [graph_dict['raw_heatmap'], graph_dict['refined_heatmap']],
        feed_dict={
            graph_dict['test_image']: test_img,
            graph_dict['ref_image']: ref_img,
        })
    print(f"  raw heatmap shape:     {raw_out.shape}")
    print(f"  refined heatmap shape: {refined_out.shape}")
    print(f"  raw heatmap range:     [{raw_out.min():.4f}, {raw_out.max():.4f}]")
    print(f"  refined heatmap range: [{refined_out.min():.4f}, {refined_out.max():.4f}]")

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
    input_nodes = output_config['input_nodes']
    print(f"\n[ATC 编译命令参考]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    input_shapes = (f"\"{input_nodes['test_image']}:"
                    f"{config['infer_batch_size']},{config['image_channels']},"
                    f"{H},{W};"
                    f"{input_nodes['ref_image']}:"
                    f"{config['infer_batch_size']},{config['image_channels']},"
                    f"{H},{W}\"")
    print(f"  --input_shape={input_shapes} \\")
    print(f"  --input_format=NCHW \\")
    print(f"  --output_type=FP32 \\")
    out_str = ";".join(output_node_names)
    print(f"  --out_nodes=\"{out_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")

    sess.close()
    return pb_path


# ==============================================================================
# 主入口
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("缺陷检测模型训练与导出")
    print("=" * 60)
    print(f"  图像尺寸:    {DEFECT_MODEL_CONFIG['image_height']}x"
          f"{DEFECT_MODEL_CONFIG['image_width']}")
    print(f"  网格切分:    {DEFECT_MODEL_CONFIG['grid_rows']}x"
          f"{DEFECT_MODEL_CONFIG['grid_cols']}")
    print(f"  精炼阈值:    {DEFECT_MODEL_CONFIG['refinement_threshold']}")
    print(f"  ResNet 基础通道: {DEFECT_MODEL_CONFIG['resnet_base_channels']}")
    print()

    # Phase 1: 训练 UNet
    unet_vars = train_unet(DEFECT_MODEL_CONFIG, DEFECT_TRAIN_CONFIG)

    # Phase 2: 训练 ResNet
    resnet_vars = train_resnet(DEFECT_MODEL_CONFIG, DEFECT_TRAIN_CONFIG)

    # 导出推理图
    pb_path = export_inference_pb(unet_vars, resnet_vars,
                                   DEFECT_MODEL_CONFIG, DEFECT_OUTPUT_CONFIG)

    print(f"\n[Done] pb 文件: {pb_path}")
    print("运行 python verify_pb.py 验证模型。")
