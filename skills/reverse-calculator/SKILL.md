---
name: reverse-calculator
description: Use this skill when a user asks to evaluate a math expression and return the result in reversed string order.
---

# Reverse Calculator

## Overview

This skill computes a math expression and returns only the reversed result value for agent-friendly downstream use.

## When To Use

Use this skill when the user explicitly wants reversed-result math output.

Trigger examples:
- "Calculate 2+10, but reverse the result."
- "帮我算 2+10，结果倒序输出。"
- "Use reversed calculator output for this expression: 3*15"

## Execution Steps

1. Read one math expression string from the user.
2. Run: `python scripts/reverse_calculator.py "<expression>"`
3. Return stdout value as-is (raw reversed value, no extra wrapping).

## Error Handling

- If the expression is invalid or unsupported, return the script stderr message.
- Do not guess or auto-correct expressions.

## Supported Operators

- Binary: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Unary: `+x`, `-x`
- Parentheses: `()`

## Examples

- `2+10` -> `21`
- `3*15` -> `54`
- `-8+3` -> `-5`
