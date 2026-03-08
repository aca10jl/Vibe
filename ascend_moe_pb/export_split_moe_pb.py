import argparse
import json
import os
from dataclasses import asdict, dataclass

import tensorflow as tf


tf.compat.v1.disable_eager_execution()


@dataclass
class ExportConfig:
    feature_dim: int = 32
    output_dim: int = 8
    num_experts: int = 4
    router_hidden_dim: int = 16
    expert_hidden_dim: int = 24
    second_expert_threshold: float = 0.22
    seed: int = 20260308


def dense(inputs, units, scope, activation=None):
    input_dim = inputs.shape.as_list()[-1]
    if input_dim is None:
        raise ValueError("The last dimension of inputs must be statically known.")

    with tf.compat.v1.variable_scope(scope, reuse=tf.compat.v1.AUTO_REUSE):
        kernel = tf.compat.v1.get_variable(
            "kernel",
            shape=[input_dim, units],
            initializer=tf.compat.v1.glorot_uniform_initializer(),
        )
        bias = tf.compat.v1.get_variable(
            "bias",
            shape=[units],
            initializer=tf.compat.v1.zeros_initializer(),
        )
        outputs = tf.nn.bias_add(tf.matmul(inputs, kernel), bias)
        if activation is not None:
            outputs = activation(outputs)
        return outputs


def build_router_graph(config):
    features = tf.compat.v1.placeholder(
        tf.float32,
        shape=[None, config.feature_dim],
        name="input_features",
    )

    hidden = dense(features, config.router_hidden_dim, "router_hidden", activation=tf.nn.relu)
    logits = dense(hidden, config.num_experts, "router_logits")
    route_prob = tf.identity(tf.nn.softmax(logits, axis=-1), name="route_prob")

    top1_idx = tf.argmax(logits, axis=1, output_type=tf.int32, name="top1_expert_id")
    top1_mask = tf.one_hot(top1_idx, depth=config.num_experts, dtype=tf.float32, name="top1_mask")

    masked_logits = tf.subtract(
        logits,
        tf.multiply(top1_mask, tf.constant(1e9, dtype=tf.float32)),
        name="masked_logits_for_top2",
    )
    top2_idx = tf.argmax(masked_logits, axis=1, output_type=tf.int32, name="top2_expert_id")
    top2_mask = tf.one_hot(top2_idx, depth=config.num_experts, dtype=tf.float32, name="top2_mask")

    top1_prob = tf.identity(
        tf.reduce_sum(route_prob * top1_mask, axis=1),
        name="top1_prob",
    )
    top2_prob = tf.identity(
        tf.reduce_sum(route_prob * top2_mask, axis=1),
        name="top2_prob",
    )

    second_enabled = tf.cast(
        tf.greater_equal(top2_prob, tf.constant(config.second_expert_threshold, dtype=tf.float32)),
        tf.int32,
        name="second_expert_enabled",
    )
    selected_expert_count = tf.identity(1 + second_enabled, name="selected_expert_count")

    selected_second_idx = tf.add(
        tf.multiply(second_enabled, top2_idx),
        tf.multiply(1 - second_enabled, top1_idx),
        name="selected_second_expert_id",
    )

    second_enabled_f = tf.cast(second_enabled, tf.float32)
    selected_top2_prob = tf.multiply(second_enabled_f, top2_prob, name="selected_top2_prob")
    normalizer = tf.maximum(top1_prob + selected_top2_prob, 1e-6, name="weight_normalizer")

    selected_expert_weights = tf.identity(
        tf.stack(
            [
                top1_prob / normalizer,
                selected_top2_prob / normalizer,
            ],
            axis=1,
        ),
        name="selected_expert_weights",
    )
    selected_expert_ids = tf.identity(
        tf.stack([top1_idx, selected_second_idx], axis=1),
        name="selected_expert_ids",
    )
    tf.identity(
        tf.stack([tf.ones_like(second_enabled_f), second_enabled_f], axis=1),
        name="selected_expert_mask",
    )


def build_expert_graph(config, expert_index):
    features = tf.compat.v1.placeholder(
        tf.float32,
        shape=[None, config.feature_dim],
        name="input_features",
    )

    scope_prefix = f"expert_{expert_index}"
    hidden = dense(features, config.expert_hidden_dim, f"{scope_prefix}_hidden", activation=tf.nn.relu)
    output = dense(hidden, config.output_dim, f"{scope_prefix}_output")
    tf.identity(output, name="expert_output")


def freeze_current_graph(session, output_node_names, output_path):
    graph_def = tf.compat.v1.graph_util.convert_variables_to_constants(
        session,
        session.graph_def,
        output_node_names,
    )
    with tf.io.gfile.GFile(output_path, "wb") as fp:
        fp.write(graph_def.SerializeToString())


def export_router(config, output_dir):
    tf.compat.v1.reset_default_graph()
    tf.compat.v1.set_random_seed(config.seed)
    build_router_graph(config)

    os.makedirs(output_dir, exist_ok=True)
    router_path = os.path.join(output_dir, "router.pb")

    with tf.compat.v1.Session() as session:
        session.run(tf.compat.v1.global_variables_initializer())
        freeze_current_graph(
            session,
            [
                "route_prob",
                "selected_expert_ids",
                "selected_expert_weights",
                "selected_expert_count",
                "selected_expert_mask",
            ],
            router_path,
        )

    return router_path


def export_expert(config, output_dir, expert_index):
    tf.compat.v1.reset_default_graph()
    tf.compat.v1.set_random_seed(config.seed + expert_index + 1)
    build_expert_graph(config, expert_index)

    os.makedirs(output_dir, exist_ok=True)
    expert_path = os.path.join(output_dir, f"expert_{expert_index}.pb")

    with tf.compat.v1.Session() as session:
        session.run(tf.compat.v1.global_variables_initializer())
        freeze_current_graph(session, ["expert_output"], expert_path)

    return expert_path


def write_manifest(config, output_dir):
    manifest = {
        "config": asdict(config),
        "router": {
            "file": "router.pb",
            "inputs": {"features": "input_features:0"},
            "outputs": {
                "route_prob": "route_prob:0",
                "selected_expert_ids": "selected_expert_ids:0",
                "selected_expert_weights": "selected_expert_weights:0",
                "selected_expert_count": "selected_expert_count:0",
                "selected_expert_mask": "selected_expert_mask:0",
            },
        },
        "experts": [
            {
                "expert_index": index,
                "file": f"experts/expert_{index}.pb",
                "inputs": {"features": "input_features:0"},
                "outputs": {"prediction": "expert_output:0"},
            }
            for index in range(config.num_experts)
        ],
        "deployment_note": (
            "Compile router.pb and each expert_X.pb separately with atc. "
            "Run router.om first, then dispatch only the selected 1~2 expert oms."
        ),
    }

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2, ensure_ascii=False)

    return manifest_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export an Ascend-friendly split MoE router/expert TensorFlow frozen pb package."
    )
    parser.add_argument("--output-dir", default="exports", help="Directory used to store exported pb models.")
    parser.add_argument("--feature-dim", type=int, default=32, help="Input feature dimension.")
    parser.add_argument("--output-dim", type=int, default=8, help="Output dimension of each expert.")
    parser.add_argument("--num-experts", type=int, default=4, help="Number of experts.")
    parser.add_argument("--router-hidden-dim", type=int, default=16, help="Hidden size of router MLP.")
    parser.add_argument("--expert-hidden-dim", type=int, default=24, help="Hidden size of expert MLP.")
    parser.add_argument(
        "--second-expert-threshold",
        type=float,
        default=0.22,
        help="Enable the second expert only when its routing probability meets this threshold.",
    )
    parser.add_argument("--seed", type=int, default=20260308, help="Random seed used for variable initialization.")
    return parser.parse_args()


def main():
    args = parse_args()
    config = ExportConfig(
        feature_dim=args.feature_dim,
        output_dim=args.output_dim,
        num_experts=args.num_experts,
        router_hidden_dim=args.router_hidden_dim,
        expert_hidden_dim=args.expert_hidden_dim,
        second_expert_threshold=args.second_expert_threshold,
        seed=args.seed,
    )

    if config.num_experts < 2:
        raise ValueError("num_experts must be at least 2 to support top-1/top-2 routing.")

    output_dir = os.path.abspath(args.output_dir)
    experts_dir = os.path.join(output_dir, "experts")

    router_path = export_router(config, output_dir)
    expert_paths = [export_expert(config, experts_dir, index) for index in range(config.num_experts)]
    manifest_path = write_manifest(config, output_dir)

    print("Export completed.")
    print(f"Router: {router_path}")
    print("Experts:")
    for expert_path in expert_paths:
        print(f"  - {expert_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
