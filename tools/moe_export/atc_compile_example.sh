#!/usr/bin/env bash
set -euo pipefail

PB_PATH=${1:-artifacts/moe_router.pb}
SOC_VERSION=${2:-Ascend310P3}

# 固定输入shape，避免ATC动态shape带来的编译问题。
atc \
  --model="${PB_PATH}" \
  --framework=3 \
  --output=artifacts/moe_router \
  --input_shape="input_features:1,32" \
  --input_format=ND \
  --soc_version="${SOC_VERSION}" \
  --log=info
