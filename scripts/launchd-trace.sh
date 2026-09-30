#!/bin/zsh
# launchd entrypoint: keep trace HTTP UI up (mlx by default via .env / TRACE_LLM_MODEL)
set -euo pipefail

ROOT="/Users/zhaowenlong/workspace/dev.self-wiki"
cd "$ROOT"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export ALLOW_PYTHON_LLM=1
export ALLOW_LOCAL_LLM=1
export LLM_PROVIDER="${LLM_PROVIDER:-local-gateway}"
export TRACE_LLM_MODEL="${TRACE_LLM_MODEL:-mlx}"
export TRACE_INDEX_TRUST_SECONDS="${TRACE_INDEX_TRUST_SECONDS:-180}"
export TRACE_TOP_K="${TRACE_TOP_K:-32}"
export TRACE_SCOPE_TOP_K="${TRACE_SCOPE_TOP_K:-64}"
export TRACE_MAX_PER_POST="${TRACE_MAX_PER_POST:-10}"
export TRACE_MAX_PER_NOTES="${TRACE_MAX_PER_NOTES:-4}"
export TRACE_MAX_PER_TWITTER="${TRACE_MAX_PER_TWITTER:-2}"

# 0.0.0.0 → Tailscale/LAN (no auth; keep off public internet)
HOST="${TRACE_HOST:-0.0.0.0}"
PORT="${TRACE_PORT:-8791}"
PY="${ROOT}/.selfwikienv/bin/python3"

exec "$PY" "${ROOT}/scripts/trace_server.py" --host "$HOST" --port "$PORT"
