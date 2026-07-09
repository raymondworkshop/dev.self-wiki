#!/bin/zsh
# Weekly launchd entrypoint: make sync → make reflect
set -euo pipefail

ROOT="/Users/zhaowenlong/workspace/dev.self-wiki"
LOG_DIR="$ROOT/self-wiki/log"
PY="$ROOT/.selfwikienv/bin/python3"

cd "$ROOT"
mkdir -p "$LOG_DIR"

# Rotate oversized launchd logs before appending more output.
"$PY" "$ROOT/scripts/log_cleanup.py" --rotate 2>/dev/null || true

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "=== $(date -Iseconds) make sync ==="
make sync

echo "=== $(date -Iseconds) make reflect ==="
make reflect

echo "=== done $(date -Iseconds) ==="
