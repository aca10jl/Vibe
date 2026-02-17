#!/usr/bin/env python3
"""Evaluate a math expression and print the reversed result value."""

import ast
import operator
import sys

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ExpressionError(ValueError):
    """Raised when an expression contains unsupported syntax."""


def evaluate_expression(expression: str):
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError("invalid expression syntax") from exc

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
            left = _eval(node.left)
            right = _eval(node.right)
            return BINARY_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
            return UNARY_OPS[type(node.op)](_eval(node.operand))
        raise ExpressionError("only numbers and + - * / // % ** () are supported")

    return _eval(tree)


def reverse_result(value) -> str:
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)

    if text.startswith("-"):
        return "-" + text[1:][::-1]
    return text[::-1]


def parse_expression(argv) -> str:
    if len(argv) < 2:
        raise ExpressionError("missing expression argument")
    return " ".join(argv[1:]).strip()


def main() -> int:
    try:
        expression = parse_expression(sys.argv)
        value = evaluate_expression(expression)
        print(reverse_result(value))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
