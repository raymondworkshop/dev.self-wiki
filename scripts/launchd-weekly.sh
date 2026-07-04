#!/bin/zsh
# Weekly launchd entrypoint: make sync → make reflect
set -euo pipefail

ROOT="/Users/zhaowenlong/workspace/dev.self-wiki"
LOG_DIR="$ROOT/self-wiki/log"

cd "$ROOT"
mkdir -p "$LOG_DIR"

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
