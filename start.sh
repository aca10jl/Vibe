#!/usr/bin/env bash
# 一键启动「一键一生 + AI 伴读助手」Demo
set -e
cd "$(dirname "$0")"

MODE="${1:-server}"

if [ "$MODE" = "static" ]; then
  echo "▶ 纯静态模式（仅本地推理，无需 Node 依赖）"
  cd web
  if command -v python3 >/dev/null 2>&1; then
    echo "  打开 http://localhost:8000"
    python3 -m http.server 8000
  else
    echo "  未找到 python3。可直接用浏览器打开 web/index.html"
  fi
  exit 0
fi

echo "▶ 全功能模式（静态托管 + 可选 Claude 代理）"
cd server
[ -d node_modules ] || { echo "  安装依赖…"; npm install; }

ENV_FLAG=""
[ -f .env ] && ENV_FLAG="--env-file=.env"
[ -f .env ] || echo "  提示：未发现 .env，Claude 模式不可用，但本地推理可正常 Demo。"

node $ENV_FLAG server.js
