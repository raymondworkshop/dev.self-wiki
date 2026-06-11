#!/bin/zsh
# Weekly launchd entrypoint: wait for local MLX, then run make sync.
set -euo pipefail

ROOT="/Users/zhaowenlong/workspace/dev.self-wiki"
MLX_HEALTH_URL="${MLX_HEALTH_URL:-http://127.0.0.1:8080/v1/models}"
MLX_WAIT_SECONDS="${MLX_WAIT_SECONDS:-600}"
MLX_POLL_SECONDS="${MLX_POLL_SECONDS:-15}"

cd "$ROOT"

wait_for_mlx() {
  local elapsed=0
  while (( elapsed < MLX_WAIT_SECONDS )); do
    if curl -sf --max-time 5 "$MLX_HEALTH_URL" >/dev/null 2>&1; then
      echo "MLX ready after ${elapsed}s"
      return 0
    fi
    sleep "$MLX_POLL_SECONDS"
    elapsed=$((elapsed + MLX_POLL_SECONDS))
  done
  echo "MLX not ready at $MLX_HEALTH_URL after ${MLX_WAIT_SECONDS}s" >&2
  return 78
}

wait_for_mlx
exec make sync
