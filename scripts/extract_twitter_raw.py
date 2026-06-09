"""Extract Twitter/X archive .js exports into raw markdown for wiki ingest."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from config import RAW_DIR

YTD_PREFIX = re.compile(r"^window\.YTD\.\S+\s*=\s*", re.DOTALL)


def load_ytd_js(path: Path) -> list:
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(YTD_PREFIX.sub("", text, count=1))


def extract_likes(data: list) -> list[dict]:
    likes = []
    for item in data:
        like = item.get("like", {})
        full_text = like.get("fullText")
        if not full_text:
            continue
        likes.append(
            {
                "tweet_id": like.get("tweetId", ""),
                "full_text": html.unescape(full_text),
                "url": like.get("expandedUrl", ""),
            }
        )
    return likes


def extract_tweets(data: list) -> list[dict]:
    tweets = []
    for item in data:
        tweet = item.get("tweet", {})
        full_text = tweet.get("full_text")
        if not full_text:
            continue
        tweets.append(
            {
                "id": tweet.get("id_str") or str(tweet.get("id", "")),
                "created_at": tweet.get("created_at", ""),
                "lang": tweet.get("lang", ""),
                "reply_to": tweet.get("in_reply_to_screen_name"),
                "full_text": html.unescape(full_text),
            }
        )
    return tweets


def extract_dms(data: list) -> list[dict]:
    messages = []
    for conv in data:
        dm = conv.get("dmConversation", {})
        conversation_id = dm.get("conversationId", "")
        for msg in dm.get("messages", []):
            mc = msg.get("messageCreate")
            if not mc or not mc.get("text"):
                continue
            messages.append(
                {
                    "conversation_id": conversation_id,
                    "id": mc.get("id", ""),
                    "created_at": mc.get("createdAt", ""),
                    "sender_id": mc.get("senderId", ""),
                    "text": html.unescape(mc["text"]),
                }
            )
    return messages


def format_like_entry(like: dict) -> str:
    lines = [f"## tweet {like['tweet_id']}"]
    if like["url"]:
        lines.append(f"- URL: {like['url']}")
    lines.append("")
    lines.append(like["full_text"])
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def format_tweet_entry(tweet: dict) -> str:
    lines = [f"## {tweet['created_at']} — tweet {tweet['id']}"]
    if tweet["lang"]:
        lines.append(f"- Lang: {tweet['lang']}")
    if tweet["reply_to"]:
        lines.append(f"- Reply to: @{tweet['reply_to']}")
    lines.append("")
    lines.append(tweet["full_text"])
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def format_dm_entry(msg: dict) -> str:
    lines = [
        f"## {msg['created_at']} — conv {msg['conversation_id']}",
        f"- Sender: {msg['sender_id']}",
        "",
        msg["text"],
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def write_likes(likes: list[dict], out_dir: Path, likes_per_file: int) -> list[Path]:
    written: list[Path] = []
    for i in range(0, len(likes), likes_per_file):
        chunk = likes[i : i + likes_per_file]
        part = i // likes_per_file + 1
        path = out_dir / f"twitter-likes-{part:03d}.md"
        header = (
            f"# Twitter Likes part {part} (extracted from like.js)\n\n"
            f"Entries {i + 1}–{i + len(chunk)} of {len(likes)}\n\n"
        )
        body = "".join(format_like_entry(like) for like in chunk)
        path.write_text(header + body, encoding="utf-8")
        written.append(path)
    return written


def write_tweets(tweets: list[dict], out_dir: Path) -> Path:
    path = out_dir / "twitter-tweets.md"
    sorted_tweets = sorted(tweets, key=lambda t: t["created_at"], reverse=True)
    header = f"# Twitter Tweets (extracted from tweets.js)\n\n{len(tweets)} tweets\n\n"
    body = "".join(format_tweet_entry(tweet) for tweet in sorted_tweets)
    path.write_text(header + body, encoding="utf-8")
    return path


def write_dms(messages: list[dict], out_dir: Path) -> Path:
    path = out_dir / "twitter-direct-messages.md"
    sorted_msgs = sorted(messages, key=lambda m: m["created_at"])
    header = (
        f"# Twitter Direct Messages (extracted from direct-messages.js)\n\n"
        f"{len(messages)} messages\n\n"
    )
    body = "".join(format_dm_entry(msg) for msg in sorted_msgs)
    path.write_text(header + body, encoding="utf-8")
    return path


def run(
    twitter_dir: Path,
    *,
    likes_per_file: int = 500,
    dry_run: bool = False,
    only: str | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {"likes": 0, "tweets": 0, "dms": 0}
    sources = {
        "likes": ("like.js", extract_likes, "likes"),
        "tweets": ("tweets.js", extract_tweets, "tweets"),
        "dms": ("direct-messages.js", extract_dms, "dms"),
    }

    for key, (filename, extractor, count_key) in sources.items():
        if only and only != key:
            continue
        src = twitter_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"Missing Twitter export: {src}")
        data = load_ytd_js(src)
        items = extractor(data)
        counts[count_key] = len(items)

        if dry_run:
            continue

        if key == "likes":
            write_likes(items, twitter_dir, likes_per_file)
        elif key == "tweets":
            write_tweets(items, twitter_dir)
        else:
            write_dms(items, twitter_dir)

    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract Twitter .js exports to raw markdown")
    parser.add_argument(
        "--twitter-dir",
        type=Path,
        default=RAW_DIR / "twitter",
        help="Directory containing Twitter .js exports",
    )
    parser.add_argument(
        "--likes-per-file",
        type=int,
        default=500,
        help="Number of likes per output markdown file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only")
    parser.add_argument(
        "--only",
        choices=["likes", "tweets", "dms"],
        help="Extract a single source type",
    )
    args = parser.parse_args(argv)

    counts = run(
        args.twitter_dir,
        likes_per_file=args.likes_per_file,
        dry_run=args.dry_run,
        only=args.only,
    )

    like_chunks = (counts["likes"] - 1) // args.likes_per_file + 1 if counts["likes"] else 0
    action = "Would write" if args.dry_run else "Wrote"
    parts = []
    if counts["likes"]:
        parts.append(f"{counts['likes']} likes ({action} {like_chunks} file(s))")
    if counts["tweets"]:
        parts.append(f"{counts['tweets']} tweets ({action} 1 file)")
    if counts["dms"]:
        parts.append(f"{counts['dms']} DMs ({action} 1 file)")
    print(", ".join(parts) or "No items extracted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
