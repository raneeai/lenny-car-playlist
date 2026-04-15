import pathlib
import unittest

from app.audio import build_audio_index, parse_rss_items
from app.ingest import build_catalog, parse_transcript_segments
from app.playlist import build_playlist, parse_query


ROOT = pathlib.Path(__file__).resolve().parents[1]


class IngestTests(unittest.TestCase):
    def test_parse_transcript_segments(self):
        markdown = """---
title: "Test"
---

**Lenny Rachitsky** (00:00:00):
Hello world.

**Guest** (00:00:15):
This is a test.
"""
        segments = parse_transcript_segments(markdown)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["speaker"], "Lenny Rachitsky")
        self.assertEqual(segments[0]["start_sec"], 0)
        self.assertEqual(segments[1]["start_sec"], 15)

    def test_build_catalog_and_playlist(self):
        catalog = build_catalog(ROOT / "data-source")
        self.assertGreaterEqual(catalog["episode_count"], 50)
        self.assertGreater(catalog["clip_count"], 0)

        parsed = parse_query("Hi Lenny, give me growth cold start clips")
        self.assertEqual(parsed["theme"], "growth")

        playlist = build_playlist("Growth cold start clips", catalog["clips"])
        self.assertGreaterEqual(len(playlist["items"]), 1)
        self.assertEqual(playlist["theme"], "growth")

    def test_parse_rss_and_build_audio_index(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <item>
      <title><![CDATA[Anthropic’s $1B to $19B growth run: how Claude became the fastest-growing AI product in history | Amol Avasare]]></title>
      <link>https://www.lennysnewsletter.com/p/example</link>
      <enclosure url="https://cdn.example.com/amol.mp3" length="123" type="audio/mpeg"/>
      <itunes:duration>3600</itunes:duration>
    </item>
  </channel>
</rss>
"""
        items = parse_rss_items(xml_text)
        self.assertEqual(len(items), 1)
        catalog = build_catalog(ROOT / "data-source")
        audio_index = build_audio_index(catalog["episodes"], items)
        self.assertIn("amol-avasare", audio_index)
        self.assertEqual(
            audio_index["amol-avasare"]["audio_url"],
            "https://cdn.example.com/amol.mp3",
        )


if __name__ == "__main__":
    unittest.main()
