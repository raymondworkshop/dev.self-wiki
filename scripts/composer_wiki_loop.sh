#!/usr/bin/env bash
# Composer wiki backfill: apply batch JSON files, pause, repeat until pending=0.
# Generate each batch JSON in Cursor (Composer) using skills/wiki-synthesize.md,
# save as self-wiki/log/pending/composer-wiki-batch-NNN.json, then run this loop.
#
# Or: agent writes batch JSON directly and invokes this script per batch.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.selfwikienv/bin/python3"
CLI="$PY $ROOT/scripts/cli.py"
BATCH_DIR="$ROOT/self-wiki/log/pending"
PAUSE="${COMPOSER_WIKI_PAUSE_SECONDS:-6}"
LIMIT="${COMPOSER_WIKI_BATCH_SIZE:-10}"

cd "$ROOT"

pending_count() {
  "$PY" -c "
from wiki_synth_manifest import list_resume_targets
print(len(list_resume_targets()))
" 2>/dev/null || echo 0
}

apply_one() {
  local f="$1"
  echo "=== Applying $f ==="
  "$PY" "$ROOT/scripts/composer_wiki_batch.py" apply "$f"
  $CLI post-ingest
  mv "$f" "${f%.json}.applied.json" 2>/dev/null || true
}

# Apply any ready batch JSON files (composer-wiki-batch-*.json)
shopt -s nullglob
for f in "$BATCH_DIR"/composer-wiki-batch-*.json; do
  [[ "$f" == *.applied.json ]] && continue
  apply_one "$f"
  echo "Sleep ${PAUSE}s..."
  sleep "$PAUSE"
done

echo "Pending: $(pending_count)"
echo "List next $LIMIT:"
"$PY" "$ROOT/scripts/composer_wiki_batch.py" list --limit "$LIMIT"
