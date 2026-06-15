"""Tests for compression provenance normalization."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from compression_provenance import fix_provenance, normalize_raw_link


def test_normalize_raw_link():
    assert normalize_raw_link("origin-apple-notes/mindset.md") == "raw/origin-apple-notes/mindset.md"
    assert normalize_raw_link("raw/_posts/a.md") == "raw/_posts/a.md"


def test_fix_apple_notes_source():
    body = "## Sources\n\n- (Source: [[origin-apple-notes/mindset.md]])\n"
    fixed = fix_provenance(body, "origin-apple-notes/mindset.md")
    assert "(Source: [[raw/origin-apple-notes/mindset.md]])" in fixed


if __name__ == "__main__":
    test_normalize_raw_link()
    test_fix_apple_notes_source()
    print("ok")
