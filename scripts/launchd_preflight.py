"""Preflight checks for launchd weekly job (writable local log/twin; vault optional)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from config import (
    LAUNCHD_DIR,
    LOG_DIR,
    TWIN_DIR,
    VAULT_DIR,
    WORKSPACE_PATH,
    ensure_workspace_dirs,
)

VAULT_PROBE = VAULT_DIR / ".launchd-write-probe"
STATUS_PATH = LOG_DIR / "launchd-weekly.status.json"


def _writable(path, *, payload: str = "ok") -> tuple[bool, str]:
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
        ("twin_dir", TWIN_DIR / ".launchd-write-probe"),
        ("launchd_dir", LAUNCHD_DIR / ".launchd-write-probe"),
    ):
        passed, err = _writable(target)
        checks[name] = {"ok": passed, "path": str(target), "error": err or None}
        ok = ok and passed

    vault_ok, vault_err = _writable(VAULT_PROBE)
    checks["vault"] = {
        "ok": vault_ok,
        "path": str(VAULT_PROBE),
        "error": vault_err or None,
        "required": False,
    }

    result = {
        "ok": ok,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    if not vault_ok:
        result["vault_hint"] = (
            "iCloud vault writes may be blocked for background launchd "
            f"(wiki under {VAULT_DIR}). "
            "System Settings → Privacy & Security → Full Disk Access → add "
            f"{WORKSPACE_PATH}/.selfwikienv/bin/python3 (or /bin/zsh). "
            "Runtime log/twin already use repo-local paths."
        )
    if not ok:
        result["hint"] = "Local log/twin/launchd dirs are not writable."
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_preflight()
    if result.get("vault_hint"):
        print(result["vault_hint"], file=sys.stderr)
    if result["ok"]:
        print("launchd preflight OK")
        return 0
    print(result.get("hint", "launchd preflight failed"), file=sys.stderr)
    for name, check in result["checks"].items():
        if not check["ok"] and check.get("required", True):
            print(f"  {name}: {check['error']}", file=sys.stderr)
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
