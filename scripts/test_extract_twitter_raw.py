import json
import tempfile
import unittest
from pathlib import Path

import extract_twitter_raw as etr


LIKE_FIXTURE = """window.YTD.like.part0 = [
  {
    "like" : {
      "tweetId" : "1",
      "fullText" : "tips:\\n&gt; be kind",
      "expandedUrl" : "https://twitter.com/i/web/status/1"
    }
  }
]"""

TWEET_FIXTURE = """window.YTD.tweets.part0 = [
  {
    "tweet" : {
      "id_str" : "99",
      "created_at" : "Sun Jun 07 09:22:57 +0000 2026",
      "lang" : "zh",
      "in_reply_to_screen_name" : "alice",
      "full_text" : "hello world"
    }
  }
]"""

DM_FIXTURE = """window.YTD.direct_messages.part0 = [
  {
    "dmConversation" : {
      "conversationId" : "a-b",
      "messages" : [
        {
          "messageCreate" : {
            "text" : "Thanks",
            "senderId" : "1",
            "id" : "10",
            "createdAt" : "2021-09-03T06:08:11.121Z"
          }
        }
      ]
    }
  }
]"""


def _parse_fixture(text: str) -> list:
    return json.loads(etr.YTD_PREFIX.sub("", text.strip(), count=1))


class ExtractTwitterRawTests(unittest.TestCase):
    def test_extract_likes_unescapes_html(self):
        likes = etr.extract_likes(_parse_fixture(LIKE_FIXTURE))
        self.assertEqual(len(likes), 1)
        self.assertIn("> be kind", likes[0]["full_text"])
        self.assertEqual(likes[0]["tweet_id"], "1")

    def test_extract_tweets_uses_snake_case_field(self):
        tweets = etr.extract_tweets(_parse_fixture(TWEET_FIXTURE))
        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0]["full_text"], "hello world")
        self.assertEqual(tweets[0]["reply_to"], "alice")

    def test_extract_dms_nested_messages(self):
        messages = etr.extract_dms(_parse_fixture(DM_FIXTURE))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "Thanks")
        self.assertEqual(messages[0]["conversation_id"], "a-b")

    def test_run_dry_run_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            twitter_dir = Path(tmp)
            (twitter_dir / "like.js").write_text(LIKE_FIXTURE, encoding="utf-8")
            (twitter_dir / "tweets.js").write_text(TWEET_FIXTURE, encoding="utf-8")
            (twitter_dir / "direct-messages.js").write_text(DM_FIXTURE, encoding="utf-8")

            counts = etr.run(twitter_dir, dry_run=True)
            self.assertEqual(counts, {"likes": 1, "tweets": 1, "dms": 1})
            self.assertEqual(list(twitter_dir.glob("*.md")), [])

    def test_run_writes_markdown_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            twitter_dir = Path(tmp)
            (twitter_dir / "like.js").write_text(LIKE_FIXTURE, encoding="utf-8")
            (twitter_dir / "tweets.js").write_text(TWEET_FIXTURE, encoding="utf-8")
            (twitter_dir / "direct-messages.js").write_text(DM_FIXTURE, encoding="utf-8")

            etr.run(twitter_dir, likes_per_file=500, dry_run=False)
            self.assertTrue((twitter_dir / "twitter-likes-001.md").exists())
            self.assertTrue((twitter_dir / "twitter-tweets.md").exists())
            self.assertTrue((twitter_dir / "twitter-direct-messages.md").exists())


if __name__ == "__main__":
    unittest.main()
