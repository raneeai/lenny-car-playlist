import pathlib
import unittest

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


if __name__ == "__main__":
    unittest.main()

