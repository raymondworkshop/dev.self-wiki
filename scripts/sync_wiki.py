"""Deprecated entrypoint — use scripts/cli.py sync (MVP thin harness)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from cli import main

if __name__ == "__main__":
    raise SystemExit(main(["sync"]))
