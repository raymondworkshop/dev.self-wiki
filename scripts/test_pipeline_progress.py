"""Tests for pipeline_progress."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from pipeline_progress import PIPELINE_ORDER, refresh_all, write_progress_md


def test_refresh_writes_progress_md():
    data = refresh_all(rescan_compression=True)
    assert "stages" in data
    for stage in PIPELINE_ORDER:
        assert stage in data["stages"]
    path = write_progress_md(data)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Pipeline progress" in text
    assert "compression" in text
    assert "discovery" in text


if __name__ == "__main__":
    test_refresh_writes_progress_md()
    print("ok")
