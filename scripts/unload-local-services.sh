#!/bin/zsh
# Unload + delete MacBook copies of Echo / LLM gateway / Trace LaunchAgents.
# Run in Terminal.app (not Cursor agent):  zsh scripts/unload-local-services.sh
set -euo pipefail

UID_N=$(id -u)
labels=(
  com.beanworkshop.echo
  com.user.llmgateway
  com.zhaowenlong.self-wiki-trace
)

for label in "${labels[@]}"; do
  plist="$HOME/Library/LaunchAgents/${label}.plist"
  echo "=== $label ==="
  launchctl bootout "gui/${UID_N}/${label}" 2>/dev/null \
    || launchctl unload "$plist" 2>/dev/null \
    || true
  if [[ -f "$plist" ]]; then
    rm -f "$plist"
    echo "removed $plist"
  else
    echo "plist already absent"
  fi
done

echo
echo "--- status ---"
for label in "${labels[@]}"; do
  if launchctl print "gui/${UID_N}/${label}" >/dev/null 2>&1; then
    echo "STILL LOADED: $label"
  else
    echo "unloaded: $label"
  fi
done

echo
echo "--- ports ---"
for port in 5050 8791 8080; do
  if curl -sf --max-time 1 "http://127.0.0.1:${port}/" >/dev/null 2>&1 \
    || curl -sf --max-time 1 "http://127.0.0.1:${port}/health" >/dev/null 2>&1 \
    || curl -sf --max-time 1 "http://127.0.0.1:${port}/v1/models" >/dev/null 2>&1; then
    echo "${port} still responding (kill leftover process if needed)"
  else
    echo "${port} down"
  fi
done
