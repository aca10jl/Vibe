# ==============================================================================
# pb 模型验证脚本
#
# 功能：
#   1. 加载 frozen pb 文件
#   2. 打印图中所有节点名（用于确认 ATC 的 input/output 节点名）
#   3. 执行一批推理，打印输出形状和路由结果
#   4. 验证路由行为：不同类型输入是否路由到不同专家
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


def load_frozen_pb(pb_path):
    """加载 frozen pb 文件，返回 GraphDef。"""
    if not os.path.exists(pb_path):
        raise FileNotFoundError(f"pb 文件不存在: {pb_path}，请先运行 train_export.py")
    with open(pb_path, 'rb') as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    return graph_def


def print_graph_nodes(graph_def, max_nodes=60):
    """打印图节点列表（用于确认节点名）。"""
    print(f"\n[节点列表] 共 {len(graph_def.node)} 个节点（显示前 {max_nodes} 个）:")
    for i, node in enumerate(graph_def.node[:max_nodes]):
        print(f"  [{i:>4d}] {node.op:20s}  {node.name}")
    if len(graph_def.node) > max_nodes:
        print(f"  ... (共 {len(graph_def.node)} 个节点)")


def verify_pb(pb_path, model_config):
    """执行推理验证。"""
    from config import OUTPUT_CONFIG

    print("=" * 60)
    print(f"验证 frozen pb: {pb_path}")
    print("=" * 60)

    graph_def = load_frozen_pb(pb_path)
    print_graph_nodes(graph_def)

    # 导入到新 Graph
    graph = tf.compat.v1.Graph()
    with graph.as_default():
        tf.import_graph_def(graph_def, name="")

    # 获取节点张量
    input_node = OUTPUT_CONFIG['input_node']
    input_tensor = graph.get_tensor_by_name(f"{input_node}:0")
    output_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][0]}:0")
    routing_indices_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][1]}:0")
    routing_weights_tensor = graph.get_tensor_by_name(f"{OUTPUT_CONFIG['output_nodes'][2]}:0")

    num_experts = model_config['num_experts']
    input_dim = model_config['input_dim']
    top_k = model_config['top_k']

    config_proto = tf.compat.v1.ConfigProto()
    config_proto.gpu_options.allow_growth = True

    with tf.compat.v1.Session(graph=graph, config=config_proto) as sess:

        # ------ 测试 1：基本推理 ------
        print("\n[Test 1] 基本推理（batch_size=4）")
        batch_size = 4
        X_test = np.random.randn(batch_size, input_dim).astype(np.float32)
        output, r_idx, r_w = sess.run(
            [output_tensor, routing_indices_tensor, routing_weights_tensor],
            feed_dict={input_tensor: X_test},
        )
        print(f"  输入 shape : {X_test.shape}")
        print(f"  输出 shape : {output.shape}")
        print(f"  路由索引  : {r_idx}  (int32, shape {r_idx.shape})")
        print(f"  路由权重  : {np.round(r_w, 4)}  (float32, shape {r_w.shape})")
        assert output.shape == (batch_size, model_config['output_dim']), \
            f"输出形状错误: {output.shape}"
        assert r_idx.shape == (batch_size, top_k), \
            f"路由索引形状错误: {r_idx.shape}"
        assert np.allclose(r_w.sum(axis=1), 1.0, atol=1e-5), \
            f"路由权重未归一化: {r_w.sum(axis=1)}"
        print("  [PASS] 形状和归一化检验通过。")

        # ------ 测试 2：batch_size=1（ATC 推理典型场景）------
        print("\n[Test 2] 单样本推理（batch_size=1，ATC 推理场景）")
        X_single = np.random.randn(1, input_dim).astype(np.float32)
        output_s, r_idx_s, r_w_s = sess.run(
            [output_tensor, routing_indices_tensor, routing_weights_tensor],
            feed_dict={input_tensor: X_single},
        )
        print(f"  输出 shape : {output_s.shape}")
        print(f"  选中专家索引: {r_idx_s[0]}  权重: {np.round(r_w_s[0], 4)}")
        assert output_s.shape == (1, model_config['output_dim'])
        print("  [PASS] 单样本推理通过。")

        # ------ 测试 3：路由差异性验证 ------
        print("\n[Test 3] 路由差异性验证（不同类别输入是否路由到不同专家）")
        large_batch = 200
        expert_counts = np.zeros(num_experts, dtype=int)
        for cls in range(num_experts):
            # 构造偏向该类别的输入
            X_cls = np.zeros((large_batch // num_experts, input_dim), dtype=np.float32)
            seg = input_dim // num_experts
            X_cls[:, cls * seg:(cls + 1) * seg] = 2.0
            X_cls += np.random.randn(large_batch // num_experts, input_dim).astype(np.float32) * 0.1

            _, r_idx_cls, _ = sess.run(
                [output_tensor, routing_indices_tensor, routing_weights_tensor],
                feed_dict={input_tensor: X_cls},
            )
            flat = r_idx_cls.flatten()
            counts = np.bincount(flat, minlength=num_experts)
            expert_counts += counts
            most_used = np.argmax(counts)
            print(
                f"  类别 {cls} 输入 -> 最常用专家 E{most_used}，"
                f"各专家激活次数: {list(counts)}"
            )

        print(f"\n  全局专家激活次数: {list(expert_counts)}")
        print(f"  标准差: {expert_counts.std():.1f}  "
              f"（越小表示路由越均衡，但初始随机权重下可能不均衡）")

        # ------ 测试 4：确定性验证 ------
        print("\n[Test 4] 确定性验证（相同输入两次推理结果一致）")
        X_fixed = np.random.randn(2, input_dim).astype(np.float32)
        out_a = sess.run(output_tensor, feed_dict={input_tensor: X_fixed})
        out_b = sess.run(output_tensor, feed_dict={input_tensor: X_fixed})
        assert np.allclose(out_a, out_b, atol=1e-6), "相同输入结果不一致！"
        print("  [PASS] 推理确定性验证通过。")

    print("\n" + "=" * 60)
    print("[ALL PASS] frozen pb 验证成功，可用于 ATC 编译。")
    print("=" * 60)

    # 打印 ATC 命令参考
    print("\n[ATC 转换命令参考]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    print(f"  --input_shape=\"{input_node}:{model_config['infer_batch_size']},{input_dim}\" \\")
    print(f"  --input_format=ND \\")
    print(f"  --output_type=FP32 \\")
    out_nodes_str = ";".join(OUTPUT_CONFIG['output_nodes'])
    print(f"  --out_nodes=\"{out_nodes_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")


if __name__ == "__main__":
    from config import MODEL_CONFIG, OUTPUT_CONFIG
    pb_path = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_CONFIG['pb_path']
    verify_pb(pb_path, MODEL_CONFIG)
