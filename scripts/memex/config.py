import re

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HASHTAG_TAG_LINE = re.compile(r"^(?:#[\w\u4e00-\u9fff-]+(?:\s+#[\w\u4e00-\u9fff-]+)*)\s*$")
HASHTAG_TOKEN = re.compile(r"#[\w\u4e00-\u9fff-]+")

FUZZY_MIN_SCORE = 50
FUZZY_SCORE_GAP = 15
SHORT_QUERY_MAX_LEN = 2
QUOTE_CHARS = "'\"“”‘’"
CJK_RE = re.compile(r"[\u3040-\u9fff\uff00-\uffef]")

SKIP_DIR_NAMES = {"pending", "__pycache__", ".obsidian"}
VAULT_LAYERS = ("raw", "wiki", "twin", "discovery", "gap", "evolution", "outputs", "log")

CONTRADICT_KEYWORDS = ["contradict", "矛盾", "冲突", "反驳", "不同于"]
SOURCE_TRAIL_RE = re.compile(r"\(Source:\s*\[\[[^\]]+\]\]\)", re.IGNORECASE)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
EVOLUTION_PATTERN = re.compile(
    r"## (?:Evolution|演进|演化)(.*?)(?=\n##|\Z)", re.IGNORECASE | re.DOTALL
)
BACKLINKS_BLOCK = re.compile(
    r"\n?## Backlinks\n<!-- BEGIN BACKLINKS -->.*?<!-- END BACKLINKS -->\n?",
    re.DOTALL,
)
