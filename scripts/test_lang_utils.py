"""Tests for lang_utils.detect_language."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from lang_utils import detect_language, epistemic_label_instruction, language_output_instruction


def test_english_only():
    assert detect_language("Hello world, this is a test.") == "English"


def test_chinese_only():
    assert detect_language("認真生活的人和拒绝无趣的灵魂") == "Chinese"


def test_predominant_chinese():
    text = "这是主要內容 " + "x" * 5
    assert detect_language(text) == "Chinese"


def test_predominant_english():
    text = "Mostly English essay about 中文"
    assert detect_language(text) == "English"


def test_instruction_contains_epistemic():
    text = epistemic_label_instruction()
    assert "[AI Synthesis]" in text
    assert "no tag" in text.lower()


def test_instruction_contains_language():
    assert "Output language: **Chinese**" in language_output_instruction("Chinese")
    assert "Do NOT translate into English" in language_output_instruction("Chinese")
