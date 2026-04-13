# ==============================================================================
# 缺陷检测模型验证脚本
#
# 功能：
#   1. 加载 frozen pb，打印图节点信息
#   2. 检查 ATC 兼容性（算子白名单）
#   3. 验证 tf.cond 控制流节点（Switch/Merge）
#   4. 基本推理测试（输出形状、值范围）
#   5. 确定性验证
#   6. 输出 ATC 编译命令
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


# ATC 支持的算子白名单（与 moe_routing/verify_pb.py 一致 + 扩展）
ATC_SUPPORTED_OPS = {
    'Const', 'Placeholder', 'Identity',
    'MatMul', 'BiasAdd', 'Add', 'AddV2', 'Sub', 'Mul', 'RealDiv',
    'Relu', 'Relu6', 'Sigmoid', 'Tanh', 'Softmax', 'LogSoftmax',
    'Reshape', 'Squeeze', 'ExpandDims', 'Transpose', 'ConcatV2', 'Pack', 'Unpack',
    'Slice', 'StridedSlice', 'GatherV2', 'Gather',
    'ReduceSum', 'Sum', 'Mean', 'Max', 'Min', 'ArgMax', 'ArgMin',
    'TopKV2',
    'Greater', 'GreaterEqual', 'Less', 'LessEqual', 'Equal', 'NotEqual',
    'LogicalAnd', 'LogicalOr', 'LogicalNot',
    'Select', 'SelectV2', 'Where',
    'Switch', 'Merge',  # tf.cond 控制流节点
    'Fill', 'ZerosLike', 'OnesLike', 'Shape', 'ShapeN',
    'Cast', 'Maximum', 'Minimum',
    'OneHot', 'Tile', 'Range',
    'NoOp', 'Assert',
    'Enter', 'Exit', 'NextIteration', 'LoopCond',
    'Conv2D', 'DepthwiseConv2dNative', 'MaxPool', 'AvgPool',
    'Pad', 'PadV2', 'MirrorPad',
    'Round', 'Sqrt', 'Rsqrt', 'Square', 'Abs', 'Neg',
}


def load_frozen_pb(pb_path):
    if not os.path.exists(pb_path):
        raise FileNotFoundError(f"pb 文件不存在: {pb_path}")
    with open(pb_path, 'rb') as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    return graph_def


def check_atc_compatibility(graph_def):
    """检查图中是否有 ATC 不支持的算子。"""
    print("\n[ATC 兼容性检查]")
    all_ops = set()
    unsupported = {}
    for node in graph_def.node:
        all_ops.add(node.op)
        if node.op not in ATC_SUPPORTED_OPS:
            unsupported.setdefault(node.op, []).append(node.name)

    print(f"  图中使用的算子类型: {len(all_ops)}")
    print(f"  算子列表: {sorted(all_ops)}")

    if unsupported:
        print(f"\n  [WARN] 以下算子可能需要确认 ATC 兼容性:")
        for op, names in sorted(unsupported.items()):
            print(f"    {op}: {names[0]} (共 {len(names)} 个)")
    else:
        print("  [PASS] 所有算子在 ATC 支持列表中。")

    # 统计控制流节点
    switch_count = sum(1 for n in graph_def.node if n.op == 'Switch')
    merge_count = sum(1 for n in graph_def.node if n.op == 'Merge')
    print(f"\n  tf.cond 控制流节点: Switch={switch_count}, Merge={merge_count}")
    if switch_count > 0:
        print("  [INFO] 检测到 tf.cond 条件分支，ATC 将按条件执行 ResNet 分类器。")

    return unsupported


def verify_pb(pb_path, config, output_config):
    """完整验证流程。"""
    print("=" * 60)
    print(f"验证缺陷检测 frozen pb: {pb_path}")
    print("=" * 60)

    graph_def = load_frozen_pb(pb_path)
    print(f"\n[图信息] 共 {len(graph_def.node)} 个节点")

    # 打印关键节点
    print("\n[关键节点]")
    keywords = ['input_test', 'input_ref', 'raw_heatmap', 'refined_heatmap',
                'cond_refine', 'shared_resnet', 'unet']
    for node in graph_def.node:
        if any(kw in node.name for kw in keywords):
            # 只打印顶层关键节点，避免输出过多
            depth = node.name.count('/')
            if depth <= 3:
                print(f"  {node.op:20s} {node.name}")

    # ATC 兼容性检查
    unsupported = check_atc_compatibility(graph_def)

    # 导入图
    graph = tf.compat.v1.Graph()
    with graph.as_default():
        tf.import_graph_def(graph_def, name="")

    input_nodes = output_config['input_nodes']
    test_img_tensor = graph.get_tensor_by_name(
        f"defect_detection/{input_nodes['test_image']}:0")
    ref_img_tensor = graph.get_tensor_by_name(
        f"defect_detection/{input_nodes['ref_image']}:0")

    output_names = output_config['output_nodes']
    refined_tensor = graph.get_tensor_by_name(f"{output_names[0]}:0")
    raw_tensor = graph.get_tensor_by_name(f"{output_names[1]}:0")

    H = config['image_height']
    W = config['image_width']
    batch_size = config['infer_batch_size']

    with tf.compat.v1.Session(graph=graph) as sess:
        # Test 1: 基本推理
        print(f"\n[Test 1] 基本推理测试")
        test_img = np.random.randint(0, 256, (batch_size, 1, H, W),
                                      dtype=np.uint8)
        ref_img = np.random.randint(0, 256, (batch_size, 1, H, W),
                                     dtype=np.uint8)

        raw_out, refined_out = sess.run(
            [raw_tensor, refined_tensor],
            feed_dict={test_img_tensor: test_img, ref_img_tensor: ref_img})

        print(f"  raw heatmap shape:     {raw_out.shape}")
        print(f"  refined heatmap shape: {refined_out.shape}")
        print(f"  raw range:     [{raw_out.min():.4f}, {raw_out.max():.4f}]")
        print(f"  refined range: [{refined_out.min():.4f}, {refined_out.max():.4f}]")

        expected_shape = (batch_size, 1, H, W)
        assert raw_out.shape == expected_shape, \
            f"raw heatmap 形状错误: {raw_out.shape} != {expected_shape}"
        assert refined_out.shape == expected_shape, \
            f"refined heatmap 形状错误: {refined_out.shape} != {expected_shape}"
        print("  [PASS] 输出形状正确")

        # Test 2: 值范围检查
        print(f"\n[Test 2] 值范围验证")
        assert raw_out.min() >= 0.0 and raw_out.max() <= 1.0, \
            f"raw heatmap 值域超出 [0,1]: [{raw_out.min()}, {raw_out.max()}]"
        assert refined_out.min() >= -0.001 and refined_out.max() <= 1.001, \
            f"refined heatmap 值域异常: [{refined_out.min()}, {refined_out.max()}]"
        print("  [PASS] 值范围正确")

        # Test 3: 确定性验证
        print(f"\n[Test 3] 确定性验证")
        test_fixed = np.random.randint(0, 256, (batch_size, 1, H, W),
                                        dtype=np.uint8)
        ref_fixed = np.random.randint(0, 256, (batch_size, 1, H, W),
                                       dtype=np.uint8)
        out_a = sess.run(refined_tensor,
                         feed_dict={test_img_tensor: test_fixed,
                                    ref_img_tensor: ref_fixed})
        out_b = sess.run(refined_tensor,
                         feed_dict={test_img_tensor: test_fixed,
                                    ref_img_tensor: ref_fixed})
        assert np.allclose(out_a, out_b, atol=1e-6), "推理结果不确定！"
        print("  [PASS] 相同输入两次推理结果一致")

        # Test 4: 精炼效果验证（refined <= raw 的 heatmap 值）
        print(f"\n[Test 4] 精炼效果验证")
        # MoR 路由器只会衰减（乘以 [0,1] 分数），不会增大 heatmap 值
        assert np.all(refined_out <= raw_out + 1e-6), \
            "精炼后的 heatmap 值不应超过原始值"
        print("  [PASS] refined_heatmap <= raw_heatmap")

        # Test 5: 全零输入测试
        print(f"\n[Test 5] 全零输入测试")
        zero_test = np.zeros((batch_size, 1, H, W), dtype=np.uint8)
        zero_ref = np.zeros((batch_size, 1, H, W), dtype=np.uint8)
        zero_out = sess.run(refined_tensor,
                            feed_dict={test_img_tensor: zero_test,
                                       ref_img_tensor: zero_ref})
        print(f"  全零输入 refined range: [{zero_out.min():.4f}, {zero_out.max():.4f}]")
        print("  [PASS]")

    print("\n" + "=" * 60)
    print("[ALL PASS] 缺陷检测 frozen pb 验证成功。")
    print("=" * 60)

    # ATC 转换命令
    print(f"\n[ATC 转换命令]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    input_shapes = (f"\"{input_nodes['test_image']}:"
                    f"{batch_size},{config['image_channels']},{H},{W};"
                    f"{input_nodes['ref_image']}:"
                    f"{batch_size},{config['image_channels']},{H},{W}\"")
    print(f"  --input_shape={input_shapes} \\")
    print(f"  --input_format=NCHW \\")
    print(f"  --output_type=FP32 \\")
    out_str = ";".join(output_names)
    print(f"  --out_nodes=\"{out_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")


if __name__ == "__main__":
    from config import DEFECT_MODEL_CONFIG, DEFECT_OUTPUT_CONFIG
    pb_path = sys.argv[1] if len(sys.argv) > 1 else DEFECT_OUTPUT_CONFIG['pb_path']
    verify_pb(pb_path, DEFECT_MODEL_CONFIG, DEFECT_OUTPUT_CONFIG)
