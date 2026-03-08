#!/usr/bin/env python3
"""Build and export a TensorFlow MoE routing model as frozen .pb.

Design goals for Ascend ATC compatibility:
1. Use TF1 graph mode and static-friendly ops.
2. Expose clear input/output node names.
3. Support automatic routing to top-1 or top-2 experts.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import tensorflow as tf


tf.compat.v1.disable_eager_execution()


@dataclass
class ModelConfig:
    input_dim: int = 16
    hidden_dim: int = 32
    output_dim: int = 4
    num_experts: int = 4
    topk_default: int = 2
    top1_confidence_threshold: float = 0.75
    seed: int = 7


def estimate_compute_cost(cfg: ModelConfig, top1_ratio: float) -> Dict[str, float]:
    """Estimate MACs/FLOPs saving when routing only 1~2 experts.

    Notes:
    - This estimation is for deployment architecture where gate and experts are served separately,
      so only selected experts are executed.
    - In a monolithic graph that always computes all experts, practical savings will not materialize.
    """
    if not 0.0 <= top1_ratio <= 1.0:
        raise ValueError("top1_ratio must be in [0, 1].")

    # Dense layer cost (MACs/sample): in_dim * out_dim
    gate_macs = cfg.input_dim * cfg.hidden_dim + cfg.hidden_dim * cfg.num_experts
    expert_macs = cfg.input_dim * cfg.hidden_dim + cfg.hidden_dim * cfg.output_dim

    full_macs = gate_macs + cfg.num_experts * expert_macs
    expected_k = top1_ratio * 1.0 + (1.0 - top1_ratio) * 2.0
    routed_macs = gate_macs + expected_k * expert_macs

    saving_ratio = 1.0 - (routed_macs / full_macs)

    # FLOPs roughly 2x MACs for multiply+add.
    return {
        "expected_k": expected_k,
        "full_macs": full_macs,
        "routed_macs": routed_macs,
        "saving_ratio": saving_ratio,
        "full_flops": full_macs * 2.0,
        "routed_flops": routed_macs * 2.0,
    }


class MoEGraphBuilder:
    def __init__(self, config: ModelConfig):
        self.cfg = config
        tf.compat.v1.set_random_seed(config.seed)

    def _dense(self, x: tf.Tensor, in_dim: int, out_dim: int, scope: str, activation=None) -> tf.Tensor:
        with tf.compat.v1.variable_scope(scope, reuse=tf.compat.v1.AUTO_REUSE):
            w = tf.compat.v1.get_variable(
                "kernel",
                shape=[in_dim, out_dim],
                initializer=tf.compat.v1.glorot_uniform_initializer(seed=self.cfg.seed),
            )
            b = tf.compat.v1.get_variable("bias", shape=[out_dim], initializer=tf.zeros_initializer())
            y = tf.matmul(x, w) + b
            return activation(y) if activation is not None else y

    def _expert(self, x: tf.Tensor, expert_id: int) -> tf.Tensor:
        h = self._dense(
            x,
            self.cfg.input_dim,
            self.cfg.hidden_dim,
            scope=f"expert_{expert_id}/dense1",
            activation=tf.nn.relu,
        )
        return self._dense(h, self.cfg.hidden_dim, self.cfg.output_dim, scope=f"expert_{expert_id}/dense2")

    def build(self) -> tf.Graph:
        graph = tf.Graph()
        with graph.as_default():
            features = tf.compat.v1.placeholder(
                tf.float32,
                shape=[None, self.cfg.input_dim],
                name="input_features",
            )

            # Optional external route override: 0 => auto routing, 1/2 => force top-k.
            route_override = tf.compat.v1.placeholder_with_default(
                tf.constant(0, dtype=tf.int32), shape=(), name="route_override"
            )

            gate_hidden = self._dense(
                features,
                self.cfg.input_dim,
                self.cfg.hidden_dim,
                scope="gate/dense1",
                activation=tf.nn.relu,
            )
            gate_logits = self._dense(
                gate_hidden,
                self.cfg.hidden_dim,
                self.cfg.num_experts,
                scope="gate/dense2",
            )
            gate_probs = tf.nn.softmax(gate_logits, axis=-1, name="gate_probs")

            top_values, top_indices = tf.nn.top_k(
                gate_probs,
                k=self.cfg.topk_default,
                sorted=True,
                name="topk_experts",
            )

            # Auto route rule: confidence high -> top1, else top2.
            max_prob = tf.reduce_max(gate_probs, axis=1, name="max_gate_prob")
            auto_k = tf.where(
                max_prob >= self.cfg.top1_confidence_threshold,
                x=tf.ones_like(max_prob, dtype=tf.int32),
                y=tf.fill(tf.shape(max_prob), tf.constant(2, tf.int32)),
                name="auto_topk",
            )

            forced_k = tf.where(
                route_override > 0,
                x=tf.fill(tf.shape(auto_k), route_override),
                y=auto_k,
            )
            chosen_k = tf.clip_by_value(forced_k, clip_value_min=1, clip_value_max=2, name="chosen_k")

            # Build expert outputs [B, E, O].
            expert_outputs: List[tf.Tensor] = []
            for i in range(self.cfg.num_experts):
                expert_outputs.append(self._expert(features, expert_id=i))
            experts_tensor = tf.stack(expert_outputs, axis=1, name="experts_tensor")

            # Mask top-1/top-2 based on chosen_k.
            rank_ids = tf.constant([1, 2], dtype=tf.int32)  # top1, top2
            rank_ids = tf.reshape(rank_ids, [1, 2])
            chosen_k_exp = tf.expand_dims(chosen_k, axis=1)
            active_rank_mask = tf.cast(rank_ids <= chosen_k_exp, tf.float32)

            masked_top_values = top_values * active_rank_mask
            normalizer = tf.reduce_sum(masked_top_values, axis=1, keepdims=True) + 1e-8
            normalized_top_values = masked_top_values / normalizer

            # Convert selected indices + weights to full expert weights [B, E].
            selected_one_hot = tf.one_hot(top_indices, depth=self.cfg.num_experts, dtype=tf.float32)
            selected_weighted = selected_one_hot * tf.expand_dims(normalized_top_values, axis=-1)
            expert_weights = tf.reduce_sum(selected_weighted, axis=1, name="expert_weights")

            # Weighted expert aggregation.
            routed_output = tf.einsum("be,beo->bo", expert_weights, experts_tensor)
            output = tf.identity(routed_output, name="model_output")

            # Useful debug/monitoring outputs for integration.
            tf.identity(top_indices, name="top_indices")
            tf.identity(top_values, name="top_values")
            tf.identity(chosen_k, name="chosen_topk")

        return graph


def freeze_graph_to_pb(graph: tf.Graph, output_path: str, output_node_names: List[str]) -> None:
    with tf.compat.v1.Session(graph=graph) as sess:
        sess.run(tf.compat.v1.global_variables_initializer())
        frozen = tf.compat.v1.graph_util.convert_variables_to_constants(
            sess,
            sess.graph_def,
            output_node_names=output_node_names,
        )
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        tf.io.write_graph(frozen, logdir=".", name=output_path, as_text=False)


def sanity_check_inference(pb_path: str, cfg: ModelConfig) -> None:
    tf.compat.v1.reset_default_graph()
    with tf.io.gfile.GFile(pb_path, "rb") as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())

    with tf.Graph().as_default() as graph:
        tf.import_graph_def(graph_def, name="")
        features = graph.get_tensor_by_name("input_features:0")
        route_override = graph.get_tensor_by_name("route_override:0")
        output = graph.get_tensor_by_name("model_output:0")
        chosen_topk = graph.get_tensor_by_name("chosen_topk:0")

        rng = np.random.default_rng(cfg.seed)
        sample = rng.normal(size=(3, cfg.input_dim)).astype(np.float32)
        with tf.compat.v1.Session(graph=graph) as sess:
            out_auto, k_auto = sess.run([output, chosen_topk], feed_dict={features: sample})
            out_force1, k_force1 = sess.run(
                [output, chosen_topk], feed_dict={features: sample, route_override: 1}
            )
            out_force2, k_force2 = sess.run(
                [output, chosen_topk], feed_dict={features: sample, route_override: 2}
            )

    print("[sanity] auto output shape:", out_auto.shape, "chosen_k:", k_auto.tolist())
    print("[sanity] force1 output shape:", out_force1.shape, "chosen_k:", k_force1.tolist())
    print("[sanity] force2 output shape:", out_force2.shape, "chosen_k:", k_force2.tolist())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export MoE TF model to frozen PB for ATC compile.")
    parser.add_argument("--output_pb", type=str, default="build/moe_router_frozen.pb")
    parser.add_argument("--input_dim", type=int, default=16)
    parser.add_argument("--hidden_dim", type=int, default=32)
    parser.add_argument("--output_dim", type=int, default=4)
    parser.add_argument("--num_experts", type=int, default=4)
    parser.add_argument("--top1_threshold", type=float, default=0.75)
    parser.add_argument(
        "--top1_ratio",
        type=float,
        default=0.7,
        help="Estimated ratio of samples routed to top-1 for compute-saving estimation.",
    )
    parser.add_argument("--skip_sanity", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ModelConfig(
        input_dim=args.input_dim,
        hidden_dim=args.hidden_dim,
        output_dim=args.output_dim,
        num_experts=args.num_experts,
        top1_confidence_threshold=args.top1_threshold,
    )

    builder = MoEGraphBuilder(cfg)
    graph = builder.build()

    outputs = [
        "model_output",
        "expert_weights",
        "top_indices",
        "top_values",
        "chosen_topk",
        "gate_probs",
    ]
    freeze_graph_to_pb(graph, args.output_pb, output_node_names=outputs)
    print(f"[export] Frozen PB saved to: {args.output_pb}")

    cost = estimate_compute_cost(cfg, top1_ratio=args.top1_ratio)
    print(
        "[cost] expected_k={expected_k:.3f}, full_macs={full_macs:.0f}, "
        "routed_macs={routed_macs:.0f}, saving={saving_ratio:.2%}".format(**cost)
    )

    if not args.skip_sanity:
        sanity_check_inference(args.output_pb, cfg)

    print("[done] You can compile with ATC, e.g.:\n"
          "atc --framework=3 --model=build/moe_router_frozen.pb "
          "--input_shape='input_features:1,16' --soc_version=Ascend310")
    print(
        "[tip] To realize compute saving on Ascend, deploy gate and experts as separate models "
        "and invoke only top-1/top-2 selected experts."
    )


if __name__ == "__main__":
    main()
