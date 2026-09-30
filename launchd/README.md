# Weekly + always-on launchd jobs

## Weekly (`com.zhaowenlong.self-wiki-weekly`)

Runs **Sunday 04:00**: `make sync` → `make reflect-launchd` (agents + ingest)

```bash
cp launchd/com.zhaowenlong.self-wiki-weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zhaowenlong.self-wiki-weekly.plist
```

Optional — wake Mac before the job (requires sudo):

```bash
sudo pmset repeat wake S 04:00:00
```

| File | Purpose |
|------|---------|
| `launchd/launchd-weekly.log` | stdout |
| `launchd/launchd-weekly.err.log` | stderr |
| `log/launchd-weekly.status.json` | last preflight / success status |

```bash
launchctl kickstart -kp gui/$(id -u)/com.zhaowenlong.self-wiki-weekly
tail -f launchd/launchd-weekly.err.log
```

## Trace HTTP (`com.zhaowenlong.self-wiki-trace`)

**Standalone product** (peer to Echo `:5050`): always-on `trace_server.py` on `0.0.0.0:8791`.
Default LLM: **gpt** (override `TRACE_LLM_MODEL=mlx`). Scoped asks: top‑16 hits + ±2 neighbors (no whole-file pad).

Tailscale: `http://100.90.225.26:8791/` (no auth — Tailscale-only).

```bash
make trace-start      # install + kickstart
make trace-stop
make trace-restart
make trace-logs       # tail launchd/launchd-trace*.log
```

| File | Purpose |
|------|---------|
| `launchd/launchd-trace.log` | stdout |
| `launchd/launchd-trace.err.log` | stderr |
| `scripts/trace_static/` | PWA manifest + icons |

Needs working [dev.local-ai](../../dev.local-ai) gateway (`mlx` on `:8080`) and `.env` with `ALLOW_LOCAL_LLM=1`.

Foreground (no launchd): `make trace-serve`.

## iCloud vault writes

Background launchd may be blocked from iCloud wiki writes unless you grant **Full Disk Access** to:

- `.selfwikienv/bin/python3`, or
- `/bin/zsh`

System Settings → Privacy & Security → Full Disk Access → add the binary → reinstall the LaunchAgent.

Runtime state stays in repo-root `log/` and `twin/` (outside iCloud).
