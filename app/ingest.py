from __future__ import annotations

import json
import pathlib
import re
from collections import Counter
from typing import Dict, List, Tuple

from app.themes import DEFAULT_THEME, THEMES

SPEAKER_LINE_RE = re.compile(r"^\*\*(.+?)\*\* \((\d{2}:\d{2}:\d{2})\):\s*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ACTIONABLE_HINTS = (
    "should",
    "need to",
    "important",
    "framework",
    "advice",
    "lesson",
    "learned",
    "tactic",
    "strategy",
    "mistake",
    "focus on",
    "how to",
)


def parse_simple_frontmatter(markdown: str) -> Dict[str, str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}
    data: Dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def strip_frontmatter(markdown: str) -> str:
    return FRONTMATTER_RE.sub("", markdown, count=1)


def hhmmss_to_seconds(value: str) -> int:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def parse_transcript_segments(markdown: str) -> List[Dict[str, object]]:
    body = strip_frontmatter(markdown)
    segments: List[Dict[str, object]] = []
    current = None
    paragraph_buffer: List[str] = []

    def flush_current() -> None:
        nonlocal current, paragraph_buffer
        if not current:
            return
        text = "\n".join(paragraph_buffer).strip()
        text = text.replace("[NEW_PARAGRAPH]", "\n\n")
        current["text"] = re.sub(r"\s+", " ", text).strip()
        if current["text"]:
            segments.append(current)
        current = None
        paragraph_buffer = []

    for line in body.splitlines():
        speaker_match = SPEAKER_LINE_RE.match(line.strip())
        if speaker_match:
            flush_current()
            current = {
                "speaker": speaker_match.group(1).strip(),
                "start_sec": hhmmss_to_seconds(speaker_match.group(2)),
            }
            continue
        if current is not None:
            paragraph_buffer.append(line)

    flush_current()

    for index, segment in enumerate(segments):
        if index + 1 < len(segments):
            segment["end_sec"] = segments[index + 1]["start_sec"]
        else:
            segment["end_sec"] = segment["start_sec"] + max(
                45, int(len(str(segment["text"]).split()) * 0.42)
            )

    return segments


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", value.lower())


def score_theme(text: str, description: str = "") -> Tuple[str, Dict[str, int]]:
    haystack = normalize_text("%s %s" % (text, description))
    theme_scores: Dict[str, int] = {}
    for theme, config in THEMES.items():
        theme_scores[theme] = sum(
            haystack.count(keyword.lower()) for keyword in config["keywords"]
        )
    chosen = max(theme_scores, key=theme_scores.get)
    if theme_scores[chosen] <= 0:
        chosen = DEFAULT_THEME
    return chosen, theme_scores


def summarize_clip(text: str, theme: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences or not sentences[0]:
        return "Actionable insight from Lenny's conversation."
    lead = sentences[0].strip()
    if len(lead) > 150:
        lead = lead[:147].rstrip() + "..."
    if theme == "growth":
        return "Growth takeaway: %s" % lead
    if theme == "ai":
        return "AI takeaway: %s" % lead
    if theme == "leadership":
        return "Leadership takeaway: %s" % lead
    if theme == "career":
        return "Career takeaway: %s" % lead
    if theme == "productivity":
        return "Productivity takeaway: %s" % lead
    return "Product takeaway: %s" % lead


def extract_subtopic(query: str, theme: str) -> str:
    normalized = normalize_text(query)
    words = [word for word in normalized.split() if len(word) > 3]
    theme_words = set(THEMES[theme]["keywords"])
    filtered = [word for word in words if word not in theme_words and word != "clips"]
    if not filtered:
        return theme
    return " ".join(filtered[:3])


def build_clip_candidates(episode: Dict[str, object]) -> List[Dict[str, object]]:
    segments = episode["segments"]
    description = str(episode.get("description", ""))
    candidates: List[Dict[str, object]] = []
    seen_ranges = set()

    for start_index in range(len(segments)):
        joined_segments = []
        for end_index in range(start_index, min(start_index + 5, len(segments))):
            joined_segments.append(segments[end_index])
            start_sec = int(joined_segments[0]["start_sec"])
            end_sec = int(joined_segments[-1]["end_sec"])
            duration = end_sec - start_sec
            if duration < 60:
                continue
            if duration > 180:
                break
            text = " ".join(str(segment["text"]) for segment in joined_segments)
            normalized = normalize_text(text)
            theme, theme_scores = score_theme(text, description)
            actionable_score = sum(normalized.count(token) for token in ACTIONABLE_HINTS)
            lenny_bonus = sum(
                1 for segment in joined_segments if segment["speaker"] == "Lenny Rachitsky"
            )
            score = (
                theme_scores.get(theme, 0) * 3
                + actionable_score * 2
                + lenny_bonus
                + min(len(text.split()) // 40, 4)
            )
            range_key = (start_sec, end_sec, theme)
            if range_key in seen_ranges:
                continue
            seen_ranges.add(range_key)
            candidates.append(
                {
                    "clip_id": "%s-%s-%s" % (episode["episode_id"], start_sec, end_sec),
                    "episode_id": episode["episode_id"],
                    "episode_title": episode["title"],
                    "guest": episode.get("guest"),
                    "theme": theme,
                    "subtopic": extract_subtopic(text[:220], theme),
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": duration,
                    "score": score,
                    "summary_short": summarize_clip(text, theme),
                    "transcript_excerpt": text[:1200].strip(),
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:18]


def build_catalog(data_source_dir: pathlib.Path) -> Dict[str, object]:
    index_path = data_source_dir / "index.json"
    source_index = json.loads(index_path.read_text())
    episodes: List[Dict[str, object]] = []
    clips: List[Dict[str, object]] = []
    clip_counter = Counter()

    for item in source_index.get("podcasts", []):
        markdown_path = data_source_dir / item["filename"]
        markdown = markdown_path.read_text()
        frontmatter = parse_simple_frontmatter(markdown)
        segments = parse_transcript_segments(markdown)
        episode_id = markdown_path.stem
        episode = {
            "episode_id": episode_id,
            "title": frontmatter.get("title", item["title"]),
            "guest": frontmatter.get("guest", item.get("guest", "")),
            "date": frontmatter.get("date", item.get("date")),
            "description": frontmatter.get("description", item.get("description", "")),
            "source_markdown_path": str(markdown_path),
            "segment_count": len(segments),
            "segments": segments,
        }
        episodes.append(episode)

        for clip in build_clip_candidates(episode):
            clip_counter[clip["theme"]] += 1
            clips.append(clip)

    episodes.sort(key=lambda item: item["date"], reverse=True)
    clips.sort(key=lambda item: (item["score"], item["duration_sec"]), reverse=True)

    lightweight_episodes = []
    for episode in episodes:
        copy = dict(episode)
        copy.pop("segments", None)
        lightweight_episodes.append(copy)

    return {
        "generated_at": source_index.get("generated_at"),
        "episode_count": len(lightweight_episodes),
        "clip_count": len(clips),
        "theme_clip_counts": dict(clip_counter),
        "episodes": lightweight_episodes,
        "clips": clips,
    }

