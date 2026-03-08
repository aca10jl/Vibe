import argparse
from collections import Counter

import tensorflow as tf


def inspect_graph(pb_path):
    with tf.io.gfile.GFile(pb_path, "rb") as fp:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(fp.read())

    op_counter = Counter(node.op for node in graph_def.node)
    print(f"graph: {pb_path}")
    print(f"nodes: {len(graph_def.node)}")
    print("ops:")
    for op_name, count in sorted(op_counter.items()):
        print(f"  {op_name}: {count}")

    placeholders = [node for node in graph_def.node if node.op == "Placeholder"]
    if placeholders:
        print("placeholders:")
        for node in placeholders:
            print(f"  {node.name}")


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect a TensorFlow frozen pb graph.")
    parser.add_argument("pb_path", help="Path to the frozen pb file.")
    return parser.parse_args()


def main():
    args = parse_args()
    inspect_graph(args.pb_path)


if __name__ == "__main__":
    main()
