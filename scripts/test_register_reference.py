"""Tests for register_reference.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from register_reference import build_catalog


def test_build_catalog_has_entries():
    catalog = build_catalog()
    assert catalog["count"] > 0
    assert catalog["entries"]
    assert catalog["entries"][0]["type"] == "external"


def test_catalog_json_serializable():
    catalog = build_catalog()
    json.dumps(catalog, ensure_ascii=False)
