"""
MoE ResNet18-UNet frozen pb 验证脚本
1. 加载 frozen pb
2. 检查 ATC 算子兼容性
3. 验证推理正确性 (确定性、路由多样性)
"""
import os
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_v2_behavior()

from config import MODEL_CONFIG, OUTPUT_CONFIG


# ATC 支持的算子白名单
ATC_SUPPORTED_OPS = {
    # 数学运算
    'MatMul', 'BatchMatMul', 'BatchMatMulV2',
    'BiasAdd', 'Add', 'AddV2', 'Sub', 'Mul', 'RealDiv',
    'Maximum', 'Minimum', 'Neg', 'Abs', 'Square', 'Sqrt', 'Rsqrt',
    'Cast', 'Floor', 'Ceil', 'Round', 'Pow', 'Exp', 'Log',
    # 激活函数
    'Relu', 'Relu6', 'Sigmoid', 'Tanh', 'Softmax', 'LogSoftmax',
    'LeakyRelu', 'Elu',
    # 卷积
    'Conv2D', 'DepthwiseConv2dNative', 'Conv2DBackpropInput',
    # 池化
    'MaxPool', 'AvgPool', 'MaxPoolV2',
    # 归一化
    'FusedBatchNorm', 'FusedBatchNormV2', 'FusedBatchNormV3',
    'Mean',
    # 控制流 (tf.cond)
    'Switch', 'Merge',
    # 形状操作
    'Reshape', 'Squeeze', 'ExpandDims', 'Transpose',
    'Slice', 'StridedSlice', 'Gather', 'GatherV2',
    'ConcatV2', 'Pack', 'Unpack', 'Tile', 'Pad', 'PadV2', 'MirrorPad',
    'Shape', 'ShapeN', 'Size', 'Rank',
    # 比较
    'Greater', 'GreaterEqual', 'Less', 'LessEqual', 'Equal', 'NotEqual',
    'LogicalAnd', 'LogicalOr', 'LogicalNot', 'Select',
    # 规约
    'Sum', 'Prod', 'ReduceSum', 'ReduceMean', 'ReduceMax', 'ReduceMin',
    'ArgMax', 'ArgMin', 'TopKV2',
    # 常量与占位
    'Const', 'Placeholder', 'Identity', 'NoOp',
    'Fill', 'ZerosLike', 'OnesLike', 'OneHot', 'Range',
    # 其他
    'ResizeBilinear', 'ResizeNearestNeighbor',
    'SpaceToBatchND', 'BatchToSpaceND',
    'DepthToSpace', 'SpaceToDepth',
}


def load_frozen_pb(pb_path):
    """加载 frozen pb"""
    with open(pb_path, 'rb') as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    return graph_def


def check_atc_compatibility(graph_def):
    """检查 ATC 算子兼容性"""
    print("\n" + "=" * 60)
    print("ATC 算子兼容性检查")
    print("=" * 60)

    ops = set()
    op_counts = {}
    for node in graph_def.node:
        ops.add(node.op)
        op_counts[node.op] = op_counts.get(node.op, 0) + 1

    # 分类
    supported = ops & ATC_SUPPORTED_OPS
    unsupported = ops - ATC_SUPPORTED_OPS

    print(f"\n总节点数: {len(graph_def.node)}")
    print(f"算子类型数: {len(ops)}")
    print(f"已支持: {len(supported)}")
    print(f"未确认: {len(unsupported)}")

    if unsupported:
        print(f"\n⚠ 未在白名单中的算子:")
        for op in sorted(unsupported):
            print(f"  - {op} (x{op_counts[op]})")
    else:
        print(f"\n✓ 所有算子都在 ATC 支持列表中")

    # 统计关键算子
    print(f"\n关键算子统计:")
    for op_name in ['Conv2D', 'Conv2DBackpropInput', 'MaxPool',
                     'FusedBatchNormV3', 'Relu', 'Switch', 'Merge',
                     'ConcatV2', 'MatMul']:
        if op_name in op_counts:
            print(f"  {op_name}: {op_counts[op_name]}")

    switch_count = op_counts.get('Switch', 0)
    merge_count = op_counts.get('Merge', 0)
    if switch_count > 0:
        print(f"\n✓ 检测到 tf.cond 控制流: Switch={switch_count}, Merge={merge_count}")
    else:
        print(f"\n✗ 未检测到 tf.cond 控制流")

    return len(unsupported) == 0


def verify_pb(pb_path, model_config):
    """验证 frozen pb"""
    print("\n" + "=" * 60)
    print(f"验证 Frozen PB: {pb_path}")
    print("=" * 60)

    graph_def = load_frozen_pb(pb_path)
    pb_size = os.path.getsize(pb_path)
    print(f"文件大小: {pb_size / 1024 / 1024:.2f} MB")

    # ATC 兼容性检查
    is_compatible = check_atc_compatibility(graph_def)

    h = model_config['image_height']
    w = model_config['image_width']
    c = model_config['image_channels']
    bs = model_config['infer_batch_size']

    graph = tf.Graph()
    with graph.as_default():
        tf.import_graph_def(graph_def, name='')

    with tf.compat.v1.Session(graph=graph) as sess:
        input_tensor = graph.get_tensor_by_name('input_image:0')
        output_tensor = graph.get_tensor_by_name('moe/output:0')
        gate_tensor = graph.get_tensor_by_name('moe/gate_class:0')

        # ========== Test 1: 基本推理 ==========
        print(f"\n--- Test 1: 基本推理 ---")
        test_input = np.random.uniform(0, 1, (bs, h, w, c)).astype(np.float32)
        out_val, cls_val = sess.run(
            [output_tensor, gate_tensor],
            feed_dict={input_tensor: test_input})
        print(f"  输入 shape: {test_input.shape}")
        print(f"  输出 shape: {out_val.shape}")
        print(f"  Gate 分类: {cls_val}")
        class_names = {0: '跳过', 1: 'Expert1(UNet-Light)', 2: 'Expert2(UNet-Heavy)'}
        print(f"  路由: {class_names.get(cls_val[0], 'unknown')}")

        assert out_val.shape == (bs, h, w, c), \
            f"输出 shape 错误: {out_val.shape} != {(bs, h, w, c)}"
        print(f"  ✓ 输出 shape 正确")

        # ========== Test 2: 确定性验证 ==========
        print(f"\n--- Test 2: 确定性验证 ---")
        out_val2, cls_val2 = sess.run(
            [output_tensor, gate_tensor],
            feed_dict={input_tensor: test_input})
        diff = np.max(np.abs(out_val - out_val2))
        print(f"  两次推理最大差异: {diff:.2e}")
        assert diff < 1e-5, f"确定性验证失败: diff={diff}"
        print(f"  ✓ 确定性验证通过")

        # ========== Test 3: 路由多样性 ==========
        print(f"\n--- Test 3: 路由多样性 ---")
        route_counts = {0: 0, 1: 0, 2: 0}
        num_tests = 50
        for _ in range(num_tests):
            rand_input = np.random.uniform(0, 1, (bs, h, w, c)).astype(np.float32)
            cls = sess.run(gate_tensor, feed_dict={input_tensor: rand_input})
            route_counts[cls[0]] = route_counts.get(cls[0], 0) + 1
        print(f"  {num_tests} 次随机输入的路由分布:")
        for k, v in sorted(route_counts.items()):
            print(f"    Class {k} ({class_names.get(k, '?')}): {v} ({v/num_tests:.0%})")

        # ========== Test 4: Class 0 跳过验证 ==========
        print(f"\n--- Test 4: 跳过逻辑验证 ---")
        # 使用简单的纯色图像来尝试触发 class 0
        simple_input = np.ones((bs, h, w, c), dtype=np.float32) * 0.5
        out_simple, cls_simple = sess.run(
            [output_tensor, gate_tensor],
            feed_dict={input_tensor: simple_input})
        print(f"  纯色输入 → Gate 分类: {cls_simple[0]} "
              f"({class_names.get(cls_simple[0], '?')})")
        if cls_simple[0] == 0:
            is_zero = np.allclose(out_simple, 0, atol=1e-5)
            print(f"  跳过时输出是否为零: {is_zero}")
            print(f"  ✓ 跳过逻辑正确" if is_zero else "  ⚠ 跳过时输出非零")
        else:
            out_max = np.max(np.abs(out_simple))
            print(f"  当前路由到 Expert, 输出 max={out_max:.4f}")
            print(f"  (纯色输入未触发跳过，模型可能学习了不同的特征)")

    print(f"\n{'=' * 60}")
    print(f"验证完成!")
    print(f"  ATC 兼容: {'✓' if is_compatible else '✗'}")
    print(f"{'=' * 60}")

    if is_compatible:
        print(f"\nATC 编译命令:")
        print(f"  atc --model={pb_path} "
              f"--framework=3 "
              f"--output=moe_resnet_unet "
              f"--soc_version=Ascend310B4 "
              f"--input_shape=\"input_image:{bs},{h},{w},{c}\"")


if __name__ == '__main__':
    verify_pb(OUTPUT_CONFIG['pb_path'], MODEL_CONFIG)
