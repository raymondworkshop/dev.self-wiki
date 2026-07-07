"""CJK search expansion via OpenCC."""

from __future__ import annotations

from memex.config import CJK_RE

_opencc_s2t = None
_opencc_t2s = None


def expand_for_search(text: str) -> str:
    if not text or not CJK_RE.search(text):
        return text
    global _opencc_s2t, _opencc_t2s
    if _opencc_s2t is None:
        from opencc import OpenCC

        _opencc_s2t = OpenCC("s2t")
        _opencc_t2s = OpenCC("t2s")
    variants = [text, _opencc_s2t.convert(text), _opencc_t2s.convert(text)]
    return "\n".join(dict.fromkeys(variants))
