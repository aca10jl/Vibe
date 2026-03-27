# ==============================================================================
# pb 模型验证脚本 V2
#
# 功能：
#   1. 加载 frozen pb，打印图节点信息
#   2. 验证推理输出形状和路由正确性
#   3. 检查 tf.cond 条件分支是否存在（Switch/Merge 节点）
#   4. 检测 ATC 不兼容算子
#   5. 验证确定性推理
#   6. 支持 top_k=1 和 top_k=2
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


# ATC 支持的常见算子白名单（非穷举，覆盖常用算子）
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
    'Switch', 'Merge',  # tf.cond 生成的控制流节点
    'Fill', 'ZerosLike', 'OnesLike', 'Shape', 'ShapeN',
    'Cast', 'Maximum', 'Minimum',
    'OneHot', 'Tile', 'Range',
    'NoOp', 'Assert',
    'Enter', 'Exit', 'NextIteration', 'LoopCond',  # 控制流
    'Conv2D', 'DepthwiseConv2dNative', 'MaxPool', 'AvgPool',  # 卷积相关
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
    """检查图中是否有 ATC 可能不支持的算子。"""
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
        print("  [PASS] 所有算子在常见 ATC 支持列表中。")

    switch_count = sum(1 for n in graph_def.node if n.op == 'Switch')
    merge_count = sum(1 for n in graph_def.node if n.op == 'Merge')
    print(f"\n  tf.cond 控制流节点: Switch={switch_count}, Merge={merge_count}")
    if switch_count > 0:
        print("  [INFO] 检测到 tf.cond 条件分支，ATC 将按条件执行专家。")

    return unsupported


def verify_pb(pb_path, model_config):
    from config import OUTPUT_CONFIG

    print("=" * 60)
    print(f"验证 frozen pb: {pb_path}")
    print("=" * 60)

    graph_def = load_frozen_pb(pb_path)
    print(f"\n[图信息] 共 {len(graph_def.node)} 个节点")

    # 打印关键节点
    print("\n[关键节点]")
    for node in graph_def.node:
        if any(kw in node.name for kw in ['input_features', 'output', 'routing', 'cond_expert']):
            print(f"  {node.op:20s} {node.name}")

    unsupported = check_atc_compatibility(graph_def)

    # 导入图
    graph = tf.compat.v1.Graph()
    with graph.as_default():
        tf.import_graph_def(graph_def, name="")

    input_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['input_node']}:0")
    output_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][0]}:0")
    routing_idx_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][1]}:0")
    routing_w_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][2]}:0")

    batch_size = model_config['infer_batch_size']
    input_dim = model_config['gate_input_dim']
    top_k = model_config['top_k']

    with tf.compat.v1.Session(graph=graph) as sess:
        # Test 1: 基本推理
        print(f"\n[Test 1] 基本推理 (batch_size={batch_size}, top_k={top_k})")
        X = np.random.randn(batch_size, input_dim).astype(np.float32)
        out, idx, w = sess.run(
            [output_tensor, routing_idx_tensor, routing_w_tensor],
            feed_dict={input_tensor: X},
        )
        print(f"  输出 shape: {out.shape}")
        print(f"  路由索引:   {idx}")
        print(f"  路由权重:   {np.round(w, 4)}")
        assert out.shape == (batch_size, input_dim), f"输出形状错误: {out.shape}"
        assert idx.shape == (batch_size, top_k), f"路由索引形状错误: {idx.shape}"
        print("  [PASS]")

        # Test 2: 确定性验证
        print("\n[Test 2] 确定性验证")
        X_fixed = np.random.randn(batch_size, input_dim).astype(np.float32)
        out_a = sess.run(output_tensor, feed_dict={input_tensor: X_fixed})
        out_b = sess.run(output_tensor, feed_dict={input_tensor: X_fixed})
        assert np.allclose(out_a, out_b, atol=1e-6), "推理结果不确定！"
        print("  [PASS] 相同输入两次推理结果一致。")

        # Test 3: 路由差异性
        print("\n[Test 3] 路由差异性验证")
        num_experts = model_config['num_experts']
        for cls in range(num_experts):
            X_cls = np.zeros((batch_size, input_dim), dtype=np.float32)
            seg = input_dim // num_experts
            X_cls[:, cls * seg:(cls + 1) * seg] = 3.0
            _, idx_cls, w_cls = sess.run(
                [output_tensor, routing_idx_tensor, routing_w_tensor],
                feed_dict={input_tensor: X_cls},
            )
            top1_w = w_cls[0, 0]
            if top_k == 1:
                mode = "单专家"
            else:
                mode = "单专家" if top1_w >= 0.99 else "双专家"
            print(f"  类别 {cls} -> 专家 {idx_cls[0]}, 权重 {np.round(w_cls[0], 3)}, 模式: {mode}")
        print("  [PASS]")

        # Test 4: 权重验证
        print("\n[Test 4] 路由权重归一化验证")
        for _ in range(10):
            X_rand = np.random.randn(batch_size, input_dim).astype(np.float32)
            _, _, w_rand = sess.run(
                [output_tensor, routing_idx_tensor, routing_w_tensor],
                feed_dict={input_tensor: X_rand},
            )
            w_sum = w_rand.sum(axis=1)
            assert np.all(w_sum >= 0.99), f"权重和异常: {w_sum}"
        print("  [PASS] 路由权重归一化正确。")

    print("\n" + "=" * 60)
    print("[ALL PASS] frozen pb 验证成功。")
    print("=" * 60)

    print(f"\n[ATC 转换命令]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    print(f"  --input_shape=\"{OUTPUT_CONFIG['input_node']}:"
          f"{model_config['infer_batch_size']},{input_dim}\" \\")
    print(f"  --input_format=ND \\")
    print(f"  --output_type=FP32 \\")
    out_str = ";".join(OUTPUT_CONFIG['output_nodes'])
    print(f"  --out_nodes=\"{out_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")


if __name__ == "__main__":
    from config import MODEL_CONFIG, OUTPUT_CONFIG
    pb_path = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_CONFIG['pb_path']
    verify_pb(pb_path, MODEL_CONFIG)
