"""Preflight checks for launchd weekly job (writable log + iCloud vault)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import LAUNCHD_DIR, LOG_DIR, WORKSPACE_PATH, ensure_workspace_dirs

VAULT_PROBE = WORKSPACE_PATH / "self-wiki" / ".launchd-write-probe"
STATUS_PATH = LOG_DIR / "launchd-weekly.status.json"


def _writable(path: Path, *, payload: str = "ok") -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        path.unlink(missing_ok=True)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def run_preflight() -> dict:
    ensure_workspace_dirs()
    LAUNCHD_DIR.mkdir(parents=True, exist_ok=True)

    checks: dict[str, dict] = {}
    ok = True

    for name, target in (
        ("log_dir", LOG_DIR / ".launchd-write-probe"),
        ("launchd_dir", LAUNCHD_DIR / ".launchd-write-probe"),
        ("vault", VAULT_PROBE),
    ):
        passed, err = _writable(target)
        checks[name] = {"ok": passed, "path": str(target), "error": err or None}
        ok = ok and passed

    result = {
        "ok": ok,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    if not ok:
        result["hint"] = (
            "iCloud vault writes blocked for background launchd. "
            "System Settings → Privacy & Security → Full Disk Access → add "
            f"{WORKSPACE_PATH}/.selfwikienv/bin/python3 (or /bin/zsh), then re-run."
        )
    STATUS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_preflight()
    if result["ok"]:
        print("launchd preflight OK")
        return 0
    print(result.get("hint", "launchd preflight failed"), file=sys.stderr)
    for name, check in result["checks"].items():
        if not check["ok"]:
            print(f"  {name}: {check['error']}", file=sys.stderr)
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
