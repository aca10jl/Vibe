#!/usr/bin/env python3
"""Build an ATC-friendly TensorFlow MoE routing graph and export frozen pb."""

import argparse
import os

import tensorflow as tf
from tensorflow.python.framework import graph_util


tf.compat.v1.disable_eager_execution()


def dense(x, in_dim, out_dim, scope, activation=None):
    with tf.compat.v1.variable_scope(scope, reuse=tf.compat.v1.AUTO_REUSE):
        w = tf.compat.v1.get_variable(
            "w",
            shape=[in_dim, out_dim],
            initializer=tf.compat.v1.glorot_uniform_initializer(seed=42),
        )
        b = tf.compat.v1.get_variable(
            "b", shape=[out_dim], initializer=tf.compat.v1.zeros_initializer()
        )
        y = tf.matmul(x, w) + b
        if activation == "relu":
            y = tf.nn.relu(y)
        return y


def build_graph(input_dim, hidden_dim, num_classes, num_experts, confidence_threshold):
    x = tf.compat.v1.placeholder(
        tf.float32, shape=[1, input_dim], name="input_features"
    )

    # Expert tower definitions (接口一致，功能相近但参数不同)
    expert_logits = []
    for idx in range(num_experts):
        h = dense(x, input_dim, hidden_dim, f"expert_{idx}/dense1", activation="relu")
        logits = dense(h, hidden_dim, num_classes, f"expert_{idx}/dense2")
        expert_logits.append(logits)

    # Router definition
    r_h = dense(x, input_dim, hidden_dim, "router/dense1", activation="relu")
    router_logits = dense(r_h, hidden_dim, num_experts, "router/dense2")
    router_probs = tf.nn.softmax(router_logits, name="router_probs")

    top_vals, top_ids = tf.math.top_k(router_probs, k=2, name="router_top2")
    top1_val = tf.identity(top_vals[0, 0], name="top1_prob")
    top1_id = tf.identity(top_ids[0, 0], name="top1_id")
    top2_id = tf.identity(top_ids[0, 1], name="top2_id")

    experts = tf.stack(expert_logits, axis=0, name="experts_stack")  # [E,1,C]
    experts = tf.squeeze(experts, axis=1, name="experts_squeezed")  # [E,C]

    top1_logits = tf.gather(experts, top1_id, axis=0, name="top1_logits")

    def route_single():
        return tf.identity(top1_logits, name="single_expert_logits")

    def route_dual():
        dual_ids = top_ids[0]
        dual_vals = top_vals[0]
        dual_logits = tf.gather(experts, dual_ids, axis=0)  # [2,C]
        weight_sum = tf.reduce_sum(dual_vals)
        norm_w = dual_vals / (weight_sum + 1e-6)
        weighted = tf.reduce_sum(dual_logits * tf.expand_dims(norm_w, -1), axis=0)
        return tf.identity(weighted, name="dual_expert_logits")

    # tf.cond 用于自动决定选择 1 个还是 2 个专家
    use_dual = tf.less(top1_val, tf.constant(confidence_threshold, tf.float32))
    final_logits = tf.cond(use_dual, route_dual, route_single, name="moe_cond_route")
    tf.nn.softmax(final_logits, name="output_probs")

    selected_expert_count = tf.cond(
        use_dual,
        lambda: tf.constant(2, dtype=tf.int32),
        lambda: tf.constant(1, dtype=tf.int32),
        name="selected_expert_count",
    )
    tf.identity(selected_expert_count, name="selected_expert_count_output")
    return x


def export_frozen_pb(output_pb, input_dim, hidden_dim, num_classes, num_experts, threshold):
    tf.compat.v1.reset_default_graph()
    tf.compat.v1.set_random_seed(42)

    build_graph(input_dim, hidden_dim, num_classes, num_experts, threshold)
    output_nodes = [
        "output_probs",
        "selected_expert_count_output",
        "top1_id",
        "top2_id",
        "top1_prob",
        "router_probs",
    ]

    with tf.compat.v1.Session() as sess:
        sess.run(tf.compat.v1.global_variables_initializer())
        frozen = graph_util.convert_variables_to_constants(
            sess, sess.graph_def, output_nodes
        )

    os.makedirs(os.path.dirname(output_pb) or ".", exist_ok=True)
    with tf.io.gfile.GFile(output_pb, "wb") as f:
        f.write(frozen.SerializeToString())

    print(f"Frozen pb saved to: {output_pb}")
    print("Input node: input_features")
    print(f"Output nodes: {', '.join(output_nodes)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_pb", default="artifacts/moe_router.pb")
    parser.add_argument("--input_dim", type=int, default=32)
    parser.add_argument("--hidden_dim", type=int, default=64)
    parser.add_argument("--num_classes", type=int, default=8)
    parser.add_argument("--num_experts", type=int, default=3)
    parser.add_argument("--confidence_threshold", type=float, default=0.75)
    args = parser.parse_args()

    export_frozen_pb(
        output_pb=args.output_pb,
        input_dim=args.input_dim,
        hidden_dim=args.hidden_dim,
        num_classes=args.num_classes,
        num_experts=args.num_experts,
        threshold=args.confidence_threshold,
    )
