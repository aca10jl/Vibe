# ==============================================================================
# MoR (Mixture of Refinement) 路由器
#
# 基于固定 4×4 网格切分 + tf.cond 条件执行的 heatmap 精炼系统。
# 核心思路：
#   1. 将 UNet 输出的 heatmap 按 4×4 网格切成 16 个 112×112 patch
#   2. 对每个 patch 计算最大值，判断是否超过阈值
#   3. 超过阈值的 patch 通过 ResNet 子模型判断是否为真实缺陷
#   4. 如果 ResNet 判断非缺陷，用 ResNet 输出分数衰减该 patch 的 heatmap 值
#
# 设计约束：
#   - 使用 tf.slice + 常量 begin/size 进行静态切分（ATC 兼容）
#   - 使用 tf.cond 生成 Switch/Merge 节点（ATC 可识别）
#   - 所有形状在图构建时静态确定
#   - ResNet 通过 tf.AUTO_REUSE 实现 16 个分支权重共享
# ==============================================================================

import tensorflow as tf

from resnet_model import build_resnet_classifier

tf.compat.v1.disable_eager_execution()
tf.compat.v1.disable_control_flow_v2()


# ==============================================================================
# 网格切分与重组
# ==============================================================================

def _extract_grid_patches(tensor, grid_rows, grid_cols, data_format='NCHW'):
    """
    将张量按固定网格切分为 patch 列表。

    使用 tf.slice + 常量 begin/size，完全静态，ATC 兼容。
    算子：Slice（在 ATC 白名单中）

    Args:
        tensor: [N, C, H, W] (NCHW) 或 [N, H, W, C] (NHWC)
        grid_rows: 网格行数
        grid_cols: 网格列数
        data_format: 'NCHW' 或 'NHWC'

    Returns:
        patches: list of (grid_rows * grid_cols) tensors,
                 每个形状为 [N, C, patch_h, patch_w] (NCHW)
                 按行优先顺序：patches[row * grid_cols + col]
    """
    shape = tensor.shape.as_list()

    if data_format == 'NCHW':
        N, C, H, W = shape
    else:
        N, H, W, C = shape

    patch_h = H // grid_rows
    patch_w = W // grid_cols

    patches = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            if data_format == 'NCHW':
                begin = [0, 0, row * patch_h, col * patch_w]
                size = [N, C, patch_h, patch_w]
            else:
                begin = [0, row * patch_h, col * patch_w, 0]
                size = [N, patch_h, patch_w, C]

            patch = tf.slice(tensor, begin, size)
            patches.append(patch)

    return patches


def _assemble_heatmap_from_patches(patches, grid_rows, grid_cols,
                                    data_format='NCHW'):
    """
    将 patch 列表重组为完整的 heatmap。

    算子：ConcatV2（在 ATC 白名单中）

    Args:
        patches: (grid_rows * grid_cols) 个张量的列表
        grid_rows: 网格行数
        grid_cols: 网格列数
        data_format: 'NCHW' 或 'NHWC'

    Returns:
        assembled: [N, C, H, W] 完整 heatmap
    """
    if data_format == 'NCHW':
        w_axis = 3  # 列方向拼接
        h_axis = 2  # 行方向拼接
    else:
        w_axis = 2
        h_axis = 1

    rows = []
    for row in range(grid_rows):
        row_patches = patches[row * grid_cols: (row + 1) * grid_cols]
        row_tensor = tf.concat(row_patches, axis=w_axis)
        rows.append(row_tensor)

    assembled = tf.concat(rows, axis=h_axis)
    return assembled


# ==============================================================================
# Cell 激活判断
# ==============================================================================

def _compute_cell_activation(heatmap_patch, threshold):
    """
    判断一个 grid cell 是否需要 ResNet 精炼。

    算子：Max (reduce_max), Greater（均在 ATC 白名单中）

    Args:
        heatmap_patch: [1, 1, patch_h, patch_w] float32
        threshold: float, 激活阈值

    Returns:
        is_active: 标量 bool tensor
    """
    max_val = tf.reduce_max(heatmap_patch)
    is_active = tf.greater(max_val, threshold)
    return is_active


# ==============================================================================
# MoR 路由器
# ==============================================================================

def build_mor_router(heatmap, test_image_float, ref_image_float, config,
                     scope='mor_router'):
    """
    构建 MoR (Mixture of Refinement) 路由器。

    对 UNet 输出的 heatmap 进行固定网格精炼：
    - 将 heatmap 和原始图像切为 4×4 共 16 个 patch
    - 对每个 patch，如果 heatmap 最大值超过阈值，触发 ResNet 分类
    - ResNet 输出缺陷概率，用于衰减 heatmap（分数衰减模式）

    类比 MoE 的 tf.cond 稀疏执行：MoE 按特征路由到不同专家，
    MoR 按空间位置路由到分类器，实现空间级条件执行。

    Args:
        heatmap: [1, 1, 448, 448] float32（UNet 输出，值域 [0,1]）
        test_image_float: [1, 1, 448, 448] float32（归一化后的待检测图）
        ref_image_float:  [1, 1, 448, 448] float32（归一化后的参考图）
        config: DEFECT_MODEL_CONFIG
        scope: 变量命名空间

    Returns:
        refined_heatmap: [1, 1, 448, 448] float32（精炼后的 heatmap）
    """
    grid_rows = config['grid_rows']
    grid_cols = config['grid_cols']
    threshold = config['refinement_threshold']
    data_format = config.get('data_format', 'NCHW')

    with tf.compat.v1.variable_scope(scope):
        # Step 1: 静态切分所有 patch
        heatmap_patches = _extract_grid_patches(heatmap, grid_rows, grid_cols,
                                                 data_format)
        test_patches = _extract_grid_patches(test_image_float, grid_rows,
                                              grid_cols, data_format)
        ref_patches = _extract_grid_patches(ref_image_float, grid_rows,
                                             grid_cols, data_format)

        # Step 2: 对每个 cell 条件执行 ResNet
        refined_patches = []
        num_cells = grid_rows * grid_cols

        for idx in range(num_cells):
            is_active = _compute_cell_activation(heatmap_patches[idx],
                                                  threshold)

            # 拼接 3 个 patch → [1, 3, 112, 112] 作为 ResNet 输入
            if data_format == 'NCHW':
                concat_axis = 1
            else:
                concat_axis = 3

            resnet_input = tf.concat([
                heatmap_patches[idx],
                test_patches[idx],
                ref_patches[idx],
            ], axis=concat_axis)

            # 为 tf.cond 构建 true_fn 和 false_fn
            # 使用默认参数捕获闭包变量，避免 late binding 问题
            def _make_true_fn(r_input, h_patch):
                def true_fn():
                    # ResNet 分类（共享权重 via AUTO_REUSE）
                    score = build_resnet_classifier(r_input, config,
                                                     scope='shared_resnet')
                    # 分数衰减：heatmap_patch *= score
                    # score 接近 1.0 → 保留（真缺陷）
                    # score 接近 0.0 → 抑制（误检）
                    attenuation = tf.reshape(score, [1, 1, 1, 1])
                    return h_patch * attenuation
                return true_fn

            def _make_false_fn(h_patch):
                def false_fn():
                    # 未触发阈值，保持原值不变
                    return h_patch
                return false_fn

            refined_patch = tf.cond(
                is_active,
                _make_true_fn(resnet_input, heatmap_patches[idx]),
                _make_false_fn(heatmap_patches[idx]),
                name=f"cond_refine_cell_{idx}",
            )
            refined_patches.append(refined_patch)

        # Step 3: 重组精炼后的 heatmap
        refined_heatmap = _assemble_heatmap_from_patches(
            refined_patches, grid_rows, grid_cols, data_format)

    return refined_heatmap


def build_mor_router_train(heatmap, test_image_float, ref_image_float, config,
                            scope='mor_router'):
    """
    训练模式的 MoR 路由器：所有 cell 无条件执行 ResNet。

    训练时不使用 tf.cond，确保梯度可以正常回传到 ResNet。
    对每个 cell 都运行 ResNet 并计算衰减，同时返回分类分数用于 BCE loss。

    Args:
        heatmap: [batch, 1, H, W] float32
        test_image_float: [batch, 1, H, W] float32
        ref_image_float:  [batch, 1, H, W] float32
        config: DEFECT_MODEL_CONFIG
        scope: 变量命名空间

    Returns:
        refined_heatmap: [batch, 1, H, W] float32
        cell_scores: list of [batch, 1] float32（每个 cell 的 ResNet 分数）
    """
    grid_rows = config['grid_rows']
    grid_cols = config['grid_cols']
    data_format = config.get('data_format', 'NCHW')

    with tf.compat.v1.variable_scope(scope):
        heatmap_patches = _extract_grid_patches(heatmap, grid_rows, grid_cols,
                                                 data_format)
        test_patches = _extract_grid_patches(test_image_float, grid_rows,
                                              grid_cols, data_format)
        ref_patches = _extract_grid_patches(ref_image_float, grid_rows,
                                             grid_cols, data_format)

        if data_format == 'NCHW':
            concat_axis = 1
        else:
            concat_axis = 3

        refined_patches = []
        cell_scores = []

        for idx in range(grid_rows * grid_cols):
            resnet_input = tf.concat([
                heatmap_patches[idx],
                test_patches[idx],
                ref_patches[idx],
            ], axis=concat_axis)

            score = build_resnet_classifier(resnet_input, config,
                                             scope='shared_resnet')
            cell_scores.append(score)

            attenuation = tf.reshape(score, [1, 1, 1, 1])
            refined_patch = heatmap_patches[idx] * attenuation
            refined_patches.append(refined_patch)

        refined_heatmap = _assemble_heatmap_from_patches(
            refined_patches, grid_rows, grid_cols, data_format)

    return refined_heatmap, cell_scores
