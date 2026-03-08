# ==============================================================================
# MoE 模型训练 + 冻结 pb 导出
#
# 流程：
#   1. 构建静态计算图（含训练节点）
#   2. 用合成数据训练若干步（演示路由分化）
#   3. convert_variables_to_constants 冻结图
#   4. 写出 frozen pb 文件
# ==============================================================================

import os
import sys
import numpy as np
import tensorflow as tf

tf.compat.v1.disable_eager_execution()

# 抑制 TF 冗余日志
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from config import MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG
from model import build_moe_graph


# ==============================================================================
# 合成数据生成（用户可替换为真实数据加载逻辑）
# ==============================================================================

def generate_synthetic_batch(batch_size, input_dim, output_dim, num_classes=4):
    """
    生成多类别合成数据，模拟不同"业务场景"（类别）对应不同的输入分布，
    促使门控网络学会根据场景路由到合适专家。
    """
    # 随机分配类别
    labels = np.random.randint(0, num_classes, size=batch_size)

    X = np.zeros((batch_size, input_dim), dtype=np.float32)
    Y = np.zeros((batch_size, output_dim), dtype=np.float32)

    for cls in range(num_classes):
        mask = (labels == cls)
        count = mask.sum()
        if count == 0:
            continue
        # 每类有不同均值，模拟业务场景差异
        mean = np.zeros(input_dim, dtype=np.float32)
        mean[cls * (input_dim // num_classes): (cls + 1) * (input_dim // num_classes)] = 1.0
        X[mask] = np.random.randn(count, input_dim).astype(np.float32) + mean * 0.5
        # 目标：不同类别有不同的输出模式
        Y[mask] = np.random.randn(count, output_dim).astype(np.float32) * 0.1
        Y[mask, cls * (output_dim // num_classes):
             (cls + 1) * (output_dim // num_classes)] += 1.0

    return X, Y


# ==============================================================================
# 负载均衡辅助损失
# ==============================================================================

def load_balancing_loss(routing_probs, num_experts, top_k):
    """
    防止门控网络退化为只选少数几个专家（路由崩溃）。

    使用 Switch Transformer 论文中的负载均衡损失：
        L_aux = num_experts * sum_i( f_i * p_i )
    其中：
        f_i = 该 batch 内被路由到专家 i 的样本比例（基于软概率近似）
        p_i = 该 batch 内专家 i 的平均路由概率
    """
    # 用软概率近似 expert utilization（可微）
    mean_probs = tf.reduce_mean(routing_probs, axis=0)  # [num_experts]
    # 理想：每个专家负载均等
    lb_loss = tf.cast(num_experts, tf.float32) * tf.reduce_sum(mean_probs * mean_probs)
    return lb_loss


# ==============================================================================
# 冻结图并保存 pb 文件
# ==============================================================================

def freeze_graph_and_save(sess, graph, output_node_names, pb_path):
    """
    将 Session 中的变量固化为常量，导出 frozen pb 文件。

    frozen pb 是 Ascend ATC 工具（--framework=3）要求的格式。
    """
    print("\n[Export] 开始冻结计算图 ...")

    # TF 2.x 中 convert_variables_to_constants 在 tf.compat.v1.graph_util 下
    convert_variables_to_constants = tf.compat.v1.graph_util.convert_variables_to_constants

    # 获取原始图定义
    graph_def = graph.as_graph_def()

    # 将变量节点替换为 Const 节点
    frozen_graph_def = convert_variables_to_constants(
        sess=sess,
        input_graph_def=graph_def,
        output_node_names=output_node_names,
    )

    # 确保输出目录存在
    os.makedirs(os.path.dirname(pb_path) if os.path.dirname(pb_path) else '.', exist_ok=True)

    # 序列化写出
    with open(pb_path, 'wb') as f:
        f.write(frozen_graph_def.SerializeToString())

    size_kb = os.path.getsize(pb_path) / 1024
    print(f"[Export] frozen pb 已保存: {pb_path}  ({size_kb:.1f} KB)")
    print(f"[Export] 冻结后节点数: {len(frozen_graph_def.node)}")

    # 打印输出节点信息，供 ATC 命令参考
    print("\n[ATC 参考信息]")
    print(f"  --model={pb_path}")
    print(f"  --framework=3")
    print(f"  --input_shape=\"{OUTPUT_CONFIG['input_node']}:"
          f"{MODEL_CONFIG['infer_batch_size']},{MODEL_CONFIG['input_dim']}\"")
    out_nodes_str = ";".join(OUTPUT_CONFIG['output_nodes'])
    print(f"  --out_nodes=\"{out_nodes_str}\"")

    return frozen_graph_def


# ==============================================================================
# 主训练 + 导出流程
# ==============================================================================

def train_and_export(model_config, train_config, output_config):
    print("=" * 60)
    print("MoE 路由模型  训练 & 导出")
    print("=" * 60)
    print(f"专家数量    : {model_config['num_experts']}")
    print(f"Top-K 路由  : {model_config['top_k']}")
    print(f"输入维度    : {model_config['input_dim']}")
    print(f"输出维度    : {model_config['output_dim']}")
    print()

    # ---- 构建静态计算图 ----
    graph = tf.compat.v1.Graph()
    with graph.as_default():

        # 输入占位符（dtype、shape 与 ATC 要求一致）
        inputs = tf.compat.v1.placeholder(
            dtype=tf.float32,
            shape=[None, model_config['input_dim']],
            name="input_tensor",
        )
        targets = tf.compat.v1.placeholder(
            dtype=tf.float32,
            shape=[None, model_config['output_dim']],
            name="target_tensor",
        )

        # 构建 MoE 模型图
        output, routing_indices, routing_weights, routing_probs = build_moe_graph(
            inputs, model_config
        )

        # ---- 损失函数 ----
        task_loss = tf.reduce_mean(tf.square(output - targets), name="task_loss")
        lb_loss = load_balancing_loss(
            routing_probs,
            model_config['num_experts'],
            model_config['top_k'],
        )
        total_loss = task_loss + train_config['lb_loss_weight'] * lb_loss

        # ---- 优化器 ----
        optimizer = tf.compat.v1.train.AdamOptimizer(
            learning_rate=train_config['learning_rate']
        )
        train_op = optimizer.minimize(total_loss)

        # ---- 初始化 ----
        init_op = tf.compat.v1.global_variables_initializer()

    # ---- 训练 ----
    config_proto = tf.compat.v1.ConfigProto()
    config_proto.gpu_options.allow_growth = True

    with tf.compat.v1.Session(graph=graph, config=config_proto) as sess:
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
                # 统计各专家被激活的频率
                flat_idx = r_idx.flatten()
                expert_counts = np.bincount(flat_idx, minlength=model_config['num_experts'])
                utilization = expert_counts / flat_idx.size
                util_str = " ".join(f"E{i}:{u:.2f}" for i, u in enumerate(utilization))
                print(
                    f"  Step {step:>4d}/{train_config['num_steps']} | "
                    f"loss={loss_val:.4f}  task={task_l:.4f}  lb={lb_l:.4f} | "
                    f"专家激活率: {util_str}"
                )

        print("[Train] 训练完成。\n")

        # ---- 冻结并保存 ----
        freeze_graph_and_save(
            sess=sess,
            graph=graph,
            output_node_names=output_config['output_nodes'],
            pb_path=output_config['pb_path'],
        )

    return output_config['pb_path']


if __name__ == "__main__":
    pb_path = train_and_export(MODEL_CONFIG, TRAIN_CONFIG, OUTPUT_CONFIG)
    print(f"\n[Done] pb 文件路径: {pb_path}")
    print("运行 verify_pb.py 验证模型推理正确性。")
