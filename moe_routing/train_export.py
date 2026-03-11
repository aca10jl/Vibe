# ==============================================================================
# MoE 模型训练 + 冻结 pb 导出
#
# 流程：
#   1. 训练阶段：使用 build_moe_graph_train（所有专家均参与，确保梯度传播）
#   2. 导出阶段：构建新的推理图 build_moe_graph（含 tf.cond 条件执行）
#   3. 从训练好的变量复制权重到推理图
#   4. 冻结导出 frozen pb
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from config import MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG
from model import build_moe_graph, build_moe_graph_train


def generate_synthetic_batch(batch_size, input_dim, output_dim, num_classes=4):
    """生成多类别合成数据，模拟不同业务场景。"""
    labels = np.random.randint(0, num_classes, size=batch_size)
    X = np.zeros((batch_size, input_dim), dtype=np.float32)
    Y = np.zeros((batch_size, output_dim), dtype=np.float32)

    for cls in range(num_classes):
        mask = (labels == cls)
        count = mask.sum()
        if count == 0:
            continue
        mean = np.zeros(input_dim, dtype=np.float32)
        seg = input_dim // num_classes
        mean[cls * seg: (cls + 1) * seg] = 1.0
        X[mask] = np.random.randn(count, input_dim).astype(np.float32) + mean * 0.5
        Y[mask] = np.random.randn(count, output_dim).astype(np.float32) * 0.1
        Y[mask, cls * (output_dim // num_classes):
             (cls + 1) * (output_dim // num_classes)] += 1.0
    return X, Y


def load_balancing_loss(routing_probs, num_experts):
    """负载均衡辅助损失，防止路由崩溃。"""
    mean_probs = tf.reduce_mean(routing_probs, axis=0)
    return tf.cast(num_experts, tf.float32) * tf.reduce_sum(mean_probs * mean_probs)


def train(model_config, train_config):
    """训练阶段：所有专家均参与计算。"""
    print("=" * 60)
    print("MoE 路由模型训练")
    print("=" * 60)
    print(f"  专家数量: {model_config['num_experts']}")
    print(f"  Top-K:    {model_config['top_k']}")
    print(f"  输入维度: {model_config['input_dim']}")
    print(f"  输出维度: {model_config['output_dim']}")
    print()

    train_graph = tf.compat.v1.Graph()
    with train_graph.as_default():
        inputs = tf.compat.v1.placeholder(tf.float32, [None, model_config['input_dim']],
                                          name="input_tensor")
        targets = tf.compat.v1.placeholder(tf.float32, [None, model_config['output_dim']],
                                           name="target_tensor")

        output, routing_indices, routing_weights, routing_probs = \
            build_moe_graph_train(inputs, model_config)

        task_loss = tf.reduce_mean(tf.square(output - targets))
        lb_loss = load_balancing_loss(routing_probs, model_config['num_experts'])
        total_loss = task_loss + train_config['lb_loss_weight'] * lb_loss

        optimizer = tf.compat.v1.train.AdamOptimizer(train_config['learning_rate'])
        train_op = optimizer.minimize(total_loss)
        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=train_graph)
    sess.run(init_op)

    print("[Train] 开始训练 ...")
    for step in range(1, train_config['num_steps'] + 1):
        X_batch, Y_batch = generate_synthetic_batch(
            train_config['train_batch_size'],
            model_config['input_dim'],
            model_config['output_dim'],
            num_classes=model_config['num_experts'],
        )
        _, loss_val, task_l, lb_l, r_idx = sess.run(
            [train_op, total_loss, task_loss, lb_loss, routing_indices],
            feed_dict={inputs: X_batch, targets: Y_batch},
        )
        if step % train_config['log_interval'] == 0 or step == 1:
            flat = r_idx.flatten()
            counts = np.bincount(flat, minlength=model_config['num_experts'])
            util = counts / flat.size
            util_str = " ".join(f"E{i}:{u:.2f}" for i, u in enumerate(util))
            print(f"  Step {step:>4d}/{train_config['num_steps']} | "
                  f"loss={loss_val:.4f} task={task_l:.4f} lb={lb_l:.4f} | {util_str}")

    print("[Train] 训练完成。\n")

    # 提取训练好的变量值
    trained_vars = {}
    for var in train_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        name = var.name  # e.g. "moe/gate/w1:0"
        # 跳过优化器变量
        if 'Adam' in name or 'beta' in name or 'power' in name:
            continue
        trained_vars[name] = sess.run(var)
    sess.close()
    return trained_vars


def export_inference_pb(trained_vars, model_config, output_config):
    """构建推理图（含 tf.cond），加载训练权重，冻结导出。"""
    print("=" * 60)
    print("构建推理图并导出 frozen pb")
    print("=" * 60)

    infer_graph = tf.compat.v1.Graph()
    with infer_graph.as_default():
        # 推理输入：固定 batch_size=1
        inputs = tf.compat.v1.placeholder(
            tf.float32,
            [model_config['infer_batch_size'], model_config['input_dim']],
            name="input_tensor",
        )

        output, routing_indices, routing_weights, routing_probs = \
            build_moe_graph(inputs, model_config)

        init_op = tf.compat.v1.global_variables_initializer()

    sess = tf.compat.v1.Session(graph=infer_graph)
    sess.run(init_op)

    # 将训练好的权重复制到推理图
    print("[Export] 加载训练权重到推理图 ...")
    loaded = 0
    for var in infer_graph.get_collection(tf.compat.v1.GraphKeys.GLOBAL_VARIABLES):
        if var.name in trained_vars:
            sess.run(var.assign(trained_vars[var.name]))
            loaded += 1
    print(f"[Export] 已加载 {loaded} 个变量。")

    # 验证推理图
    print("[Export] 验证推理图 ...")
    test_input = np.random.randn(model_config['infer_batch_size'],
                                  model_config['input_dim']).astype(np.float32)
    out_val, idx_val, w_val = sess.run(
        [output, routing_indices, routing_weights],
        feed_dict={inputs: test_input},
    )
    print(f"  输出 shape: {out_val.shape}")
    print(f"  路由索引:   {idx_val}")
    print(f"  路由权重:   {np.round(w_val, 4)}")

    # 冻结导出
    pb_path = output_config['pb_path']
    output_node_names = output_config['output_nodes']

    graph_def = infer_graph.as_graph_def()
    frozen_def = tf.compat.v1.graph_util.convert_variables_to_constants(
        sess, graph_def, output_node_names,
    )

    os.makedirs(os.path.dirname(pb_path) if os.path.dirname(pb_path) else '.', exist_ok=True)
    with open(pb_path, 'wb') as f:
        f.write(frozen_def.SerializeToString())

    size_kb = os.path.getsize(pb_path) / 1024
    print(f"\n[Export] frozen pb 已保存: {pb_path} ({size_kb:.1f} KB)")
    print(f"[Export] 冻结后节点数: {len(frozen_def.node)}")

    # 打印 ATC 编译参考信息
    print("\n[ATC 编译命令参考]")
    print(f"atc \\")
    print(f"  --model={pb_path} \\")
    print(f"  --framework=3 \\")
    print(f"  --output={os.path.splitext(pb_path)[0]} \\")
    print(f"  --input_shape=\"{output_config['input_node']}:"
          f"{model_config['infer_batch_size']},{model_config['input_dim']}\" \\")
    print(f"  --input_format=ND \\")
    print(f"  --output_type=FP32 \\")
    out_str = ";".join(output_config['output_nodes'])
    print(f"  --out_nodes=\"{out_str}\" \\")
    print(f"  --log=info \\")
    print(f"  --soc_version=Ascend310")

    sess.close()
    return pb_path


if __name__ == "__main__":
    trained_vars = train(MODEL_CONFIG, TRAIN_CONFIG)
    pb_path = export_inference_pb(trained_vars, MODEL_CONFIG, OUTPUT_CONFIG)
    print(f"\n[Done] pb 文件: {pb_path}")
    print("运行 python verify_pb.py 验证模型。")
