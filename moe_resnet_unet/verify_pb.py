# ==============================================================================
# MoE ResNet18 + UNet 模型 pb 验证脚本
#
# 验证项：
#   1. 加载 frozen pb 并打印图信息
#   2. ATC 算子兼容性检查
#   3. 推理验证（输出形状、路由类别）
#   4. 确定性验证（相同输入 -> 相同输出）
#   5. 路由差异性验证（不同类型输入路由到不同类别）
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from config import MODEL_CONFIG, OUTPUT_CONFIG


# Ascend CANN ATC 支持的 TF 算子白名单（扩展版，包含 UNet/ResNet 所需算子）
ATC_SUPPORTED_OPS = {
    # 基础运算
    'Const', 'Identity', 'Placeholder',
    'MatMul', 'BiasAdd', 'Add', 'AddV2', 'Sub', 'Mul', 'RealDiv',
    'Neg', 'Abs', 'Square', 'Sqrt', 'Rsqrt',
    # 激活函数
    'Relu', 'Relu6', 'Sigmoid', 'Tanh', 'Softmax', 'LeakyRelu',
    # 卷积
    'Conv2D', 'DepthwiseConv2dNative',
    # 池化
    'MaxPool', 'AvgPool', 'Mean',
    # 归一化
    'FusedBatchNorm', 'FusedBatchNormV2', 'FusedBatchNormV3',
    # 形状操作
    'Reshape', 'Transpose', 'ConcatV2', 'Pack', 'Unpack',
    'Slice', 'StridedSlice', 'Squeeze', 'ExpandDims',
    'Shape', 'Fill', 'Tile',
    # 比较 / 逻辑
    'Greater', 'GreaterEqual', 'Less', 'LessEqual', 'Equal',
    'LogicalAnd', 'LogicalOr', 'LogicalNot',
    # 规约
    'Sum', 'Max', 'Min', 'ArgMax',
    # 类型转换
    'Cast',
    # 控制流 (tf.cond / tf.case)
    'Switch', 'Merge', 'Select',
    # 上采样
    'ResizeNearestNeighbor', 'ResizeBilinear',
    # 其他
    'Pad', 'MirrorPad', 'Maximum', 'Minimum',
    'NoOp', 'Assign', 'AssignSub',
}


def load_frozen_pb(pb_path):
    """加载 frozen pb 文件。"""
    graph = tf.compat.v1.Graph()
    with graph.as_default():
        graph_def = tf.compat.v1.GraphDef()
        with open(pb_path, 'rb') as f:
            graph_def.ParseFromString(f.read())
        tf.import_graph_def(graph_def, name='')
    return graph, graph_def


def check_atc_compatibility(graph_def):
    """检查所有算子是否在 ATC 支持列表中。"""
    unsupported = {}
    switch_merge_count = 0

    for node in graph_def.node:
        op = node.op
        if op in ('Switch', 'Merge'):
            switch_merge_count += 1
        if op not in ATC_SUPPORTED_OPS:
            unsupported[op] = unsupported.get(op, 0) + 1

    return unsupported, switch_merge_count


def verify_pb(pb_path=None, model_config=None, output_config=None):
    """验证 frozen pb 模型。"""
    if pb_path is None:
        pb_path = OUTPUT_CONFIG['pb_path']
    if model_config is None:
        model_config = MODEL_CONFIG
    if output_config is None:
        output_config = OUTPUT_CONFIG

    print("=" * 60)
    print(f"验证 MoE ResNet18 + UNet 模型: {pb_path}")
    print("=" * 60)

    if not os.path.exists(pb_path):
        print(f"[Error] pb 文件不存在: {pb_path}")
        return False

    # 1. 加载图
    graph, graph_def = load_frozen_pb(pb_path)
    print(f"\n[1] 图信息:")
    print(f"  节点数: {len(graph_def.node)}")
    size_kb = os.path.getsize(pb_path) / 1024
    print(f"  文件大小: {size_kb:.1f} KB")

    # 列出关键节点
    key_names = [output_config['input_node']] + output_config['output_nodes']
    for name in key_names:
        try:
            tensor = graph.get_tensor_by_name(f"{name}:0")
            print(f"  {name}: shape={tensor.shape}, dtype={tensor.dtype.name}")
        except KeyError:
            print(f"  {name}: [未找到]")

    # 2. ATC 兼容性检查
    print(f"\n[2] ATC 兼容性检查:")
    unsupported, sw_count = check_atc_compatibility(graph_def)
    print(f"  Switch/Merge 节点数: {sw_count} (tf.cond/tf.case 条件分支)")
    if unsupported:
        print(f"  [警告] 可能不支持的算子:")
        for op, cnt in sorted(unsupported.items()):
            print(f"    {op}: {cnt}")
    else:
        print(f"  所有算子均在 ATC 白名单中。")

    # 3. 基础推理验证
    print(f"\n[3] 基础推理验证:")
    img_shape = model_config['image_shape']
    bs = model_config['infer_batch_size']

    sess = tf.compat.v1.Session(graph=graph)
    input_tensor = graph.get_tensor_by_name(
        f"{output_config['input_node']}:0")

    output_tensors = {}
    for name in output_config['output_nodes']:
        output_tensors[name] = graph.get_tensor_by_name(f"{name}:0")

    # 随机输入测试
    test_input = np.random.randn(bs, img_shape[1], img_shape[2],
                                  img_shape[3]).astype(np.float32) * 0.1
    results = sess.run(output_tensors, feed_dict={input_tensor: test_input})

    for name, val in results.items():
        if isinstance(val, np.ndarray):
            print(f"  {name}: shape={val.shape}, "
                  f"min={val.min():.4f}, max={val.max():.4f}")
        else:
            print(f"  {name}: {val}")
    print(f"  [OK] 基础推理成功")

    # 4. 确定性验证
    print(f"\n[4] 确定性验证:")
    results2 = sess.run(output_tensors, feed_dict={input_tensor: test_input})
    all_same = True
    for name in output_tensors:
        v1 = results[name]
        v2 = results2[name]
        if isinstance(v1, np.ndarray):
            if not np.allclose(v1, v2, atol=1e-6):
                print(f"  {name}: [不确定!] max_diff="
                      f"{np.max(np.abs(v1 - v2)):.8f}")
                all_same = False
        else:
            if v1 != v2:
                all_same = False
    if all_same:
        print(f"  [OK] 相同输入产生相同输出")
    else:
        print(f"  [警告] 检测到非确定性行为")

    # 5. 路由差异性验证
    print(f"\n[5] 路由差异性验证:")

    # 低噪声输入（期望 class 0 = 跳过）
    blank_input = np.random.rand(bs, img_shape[1], img_shape[2],
                                  img_shape[3]).astype(np.float32) * 0.02
    r_blank = sess.run(output_tensors, feed_dict={input_tensor: blank_input})

    # 中等复杂度输入
    simple_input = np.zeros((bs, img_shape[1], img_shape[2],
                              img_shape[3]), dtype=np.float32)
    simple_input[:, :, 50:150, 50:150] = 0.8
    r_simple = sess.run(output_tensors, feed_dict={input_tensor: simple_input})

    # 高复杂度输入
    complex_input = np.random.randn(bs, img_shape[1], img_shape[2],
                                     img_shape[3]).astype(np.float32) * 0.5
    for _ in range(5):
        y0, x0 = np.random.randint(0, img_shape[2] - 30), \
                 np.random.randint(0, img_shape[3] - 30)
        complex_input[:, :, y0:y0 + 30, x0:x0 + 30] += 0.6
    r_complex = sess.run(output_tensors,
                          feed_dict={input_tensor: complex_input})

    cls_blank = r_blank['moe/routing_class']
    cls_simple = r_simple['moe/routing_class']
    cls_complex = r_complex['moe/routing_class']
    print(f"  空白图像路由:   class {cls_blank}")
    print(f"  简单图像路由:   class {cls_simple}")
    print(f"  复杂图像路由:   class {cls_complex}")

    # 检查跳过类别的输出是否接近零
    if cls_blank == 0:
        out_blank = r_blank['moe/output']
        if np.max(np.abs(out_blank)) < 1e-5:
            print(f"  [OK] class 0 输出接近全零 (max={np.max(np.abs(out_blank)):.8f})")
        else:
            print(f"  [注意] class 0 输出非零 (max={np.max(np.abs(out_blank)):.4f})")

    # 检查路由多样性
    classes_seen = set()
    classes_seen.add(int(cls_blank))
    classes_seen.add(int(cls_simple))
    classes_seen.add(int(cls_complex))
    if len(classes_seen) >= 2:
        print(f"  [OK] 路由具有多样性 (观察到类别: {sorted(classes_seen)})")
    else:
        print(f"  [注意] 路由多样性不足 (仅观察到类别: {sorted(classes_seen)})")
        print(f"         这可能是合成数据训练不充分导致，实际部署时应使用真实数据验证")

    sess.close()

    # ATC 编译命令
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

    print(f"\n{'=' * 60}")
    print(f"验证完成。")
    return True


if __name__ == "__main__":
    verify_pb()
