# ==============================================================================
# 缺陷检测模型 —— 顶层图构建
#
# 组装 UNet（主模型）+ MoR Router + ResNet（子模型）为完整的计算图。
#
# 推理图：UNet → heatmap → MoR Router（tf.cond 条件执行）→ refined_heatmap
# 训练图：分两阶段，UNet 和 ResNet 分别训练
#
# 设计约束：
#   - tf.compat.v1 静态图，可导出 frozen pb
#   - 仅使用 Ascend CANN ATC 支持的算子
#   - 固定 batch_size=1 用于推理
# ==============================================================================

import tensorflow as tf

from unet_model import build_unet
from mor_router import build_mor_router, build_mor_router_train

tf.compat.v1.disable_eager_execution()
tf.compat.v1.disable_control_flow_v2()


# ==============================================================================
# 推理图构建
# ==============================================================================

def build_defect_detection_graph(config):
    """
    构建完整的缺陷检测推理图（含 tf.cond MoR 路由）。

    图结构：
      input_test_image [1,1,448,448] UINT8 ─┐
                                              ├→ UNet → heatmap [1,1,448,448] float32
      input_ref_image  [1,1,448,448] UINT8 ─┘         │
                                                       ├→ MoR Router (16 × tf.cond)
                                                       │   └→ ResNet (共享权重)
                                                       └→ refined_heatmap [1,1,448,448]

    Args:
        config: DEFECT_MODEL_CONFIG

    Returns:
        dict: {
            'test_image': placeholder,
            'ref_image': placeholder,
            'raw_heatmap': UNet 原始输出,
            'refined_heatmap': MoR 精炼后输出,
        }
    """
    batch_size = config['infer_batch_size']
    H = config['image_height']
    W = config['image_width']
    C = config['image_channels']

    with tf.compat.v1.variable_scope("defect_detection"):
        # 输入 placeholder
        test_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_test_image")
        ref_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_ref_image")

        # UNet 主模型
        heatmap, test_float, ref_float = build_unet(
            test_image, ref_image, config, scope="unet")

        raw_heatmap = tf.identity(heatmap, name="raw_heatmap")

        # MoR 路由器
        refined_heatmap = build_mor_router(
            heatmap, test_float, ref_float, config, scope="mor_router")

        refined_heatmap = tf.identity(refined_heatmap, name="refined_heatmap")

    return {
        'test_image': test_image,
        'ref_image': ref_image,
        'raw_heatmap': raw_heatmap,
        'refined_heatmap': refined_heatmap,
    }


# ==============================================================================
# 训练图构建
# ==============================================================================

def build_unet_train_graph(config, batch_size=None):
    """
    构建 UNet 训练图（Phase 1）。

    Args:
        config: DEFECT_MODEL_CONFIG
        batch_size: 训练 batch 大小，默认使用 config 中的值

    Returns:
        dict: {
            'test_image': placeholder,
            'ref_image': placeholder,
            'gt_heatmap': placeholder,
            'heatmap': UNet 输出,
            'loss': 训练损失,
        }
    """
    if batch_size is None:
        batch_size = config['infer_batch_size']
    H = config['image_height']
    W = config['image_width']
    C = config['image_channels']

    with tf.compat.v1.variable_scope("defect_detection"):
        test_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_test_image")
        ref_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_ref_image")
        gt_heatmap = tf.compat.v1.placeholder(
            tf.float32, [batch_size, 1, H, W], name="gt_heatmap")

        heatmap, _, _ = build_unet(test_image, ref_image, config, scope="unet")

        # 二元交叉熵 + MSE 混合损失
        eps = 1e-7
        bce_loss = -tf.reduce_mean(
            gt_heatmap * tf.math.log(heatmap + eps) +
            (1.0 - gt_heatmap) * tf.math.log(1.0 - heatmap + eps))
        mse_loss = tf.reduce_mean(tf.square(heatmap - gt_heatmap))
        loss = bce_loss + mse_loss

    return {
        'test_image': test_image,
        'ref_image': ref_image,
        'gt_heatmap': gt_heatmap,
        'heatmap': heatmap,
        'loss': loss,
    }


def build_resnet_train_graph(config, batch_size=None):
    """
    构建 ResNet 训练图（Phase 2）。

    使用训练模式的 MoR（无 tf.cond，所有 cell 无条件执行），
    确保梯度可以正常回传。

    Args:
        config: DEFECT_MODEL_CONFIG
        batch_size: 训练 batch 大小

    Returns:
        dict: {
            'test_image': placeholder,
            'ref_image': placeholder,
            'gt_heatmap': placeholder（可用 UNet 输出代替）,
            'gt_cell_labels': placeholder [batch, 16],
            'refined_heatmap': 精炼后的 heatmap,
            'cell_scores': 每个 cell 的 ResNet 分数,
            'loss': 训练损失,
        }
    """
    if batch_size is None:
        batch_size = config['infer_batch_size']
    H = config['image_height']
    W = config['image_width']
    C = config['image_channels']
    num_cells = config['grid_rows'] * config['grid_cols']

    with tf.compat.v1.variable_scope("defect_detection"):
        test_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_test_image")
        ref_image = tf.compat.v1.placeholder(
            tf.uint8, [batch_size, C, H, W], name="input_ref_image")

        # heatmap 输入（可以是 UNet 的输出或真实标签）
        heatmap_input = tf.compat.v1.placeholder(
            tf.float32, [batch_size, 1, H, W], name="heatmap_input")

        # 每个 cell 的真实标签（1.0 = 真缺陷，0.0 = 误检）
        gt_cell_labels = tf.compat.v1.placeholder(
            tf.float32, [batch_size, num_cells], name="gt_cell_labels")

        # 归一化
        test_float = tf.cast(test_image, tf.float32) / 255.0
        ref_float = tf.cast(ref_image, tf.float32) / 255.0

        # 训练模式 MoR（无 tf.cond）
        refined_heatmap, cell_scores = build_mor_router_train(
            heatmap_input, test_float, ref_float, config, scope="mor_router")

        # 计算分类损失（BCE loss 对每个 cell）
        eps = 1e-7
        total_loss = tf.constant(0.0, dtype=tf.float32)
        for idx in range(num_cells):
            score = cell_scores[idx]            # [batch, 1]
            label = gt_cell_labels[:, idx:idx+1]  # [batch, 1]
            cell_bce = -tf.reduce_mean(
                label * tf.math.log(score + eps) +
                (1.0 - label) * tf.math.log(1.0 - score + eps))
            total_loss = total_loss + cell_bce

        loss = total_loss / float(num_cells)

    return {
        'test_image': test_image,
        'ref_image': ref_image,
        'heatmap_input': heatmap_input,
        'gt_cell_labels': gt_cell_labels,
        'refined_heatmap': refined_heatmap,
        'cell_scores': cell_scores,
        'loss': loss,
    }
