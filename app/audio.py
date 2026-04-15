from __future__ import annotations

import json
import pathlib
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional

RSS_URL = "https://api.substack.com/feed/podcast/10845.rss"


@dataclass
class AudioItem:
    title: str
    audio_url: str
    duration_sec: Optional[int]
    link: str


def normalize_title(value: str) -> str:
    cleaned = value.lower()
    cleaned = cleaned.replace("’", "'").replace("“", '"').replace("”", '"')
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fetch_rss_xml(rss_url: str = RSS_URL) -> str:
    request = urllib.request.Request(
        rss_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_rss_items(xml_text: str) -> List[AudioItem]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    items: List[AudioItem] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        duration_text = None
        for child in item:
            if child.tag.endswith("duration"):
                duration_text = (child.text or "").strip()
                break
        duration_sec = None
        if duration_text and duration_text.isdigit():
            duration_sec = int(duration_text)

        enclosure = item.find("enclosure")
        if not title or enclosure is None:
            continue
        audio_url = enclosure.attrib.get("url", "").strip()
        if not audio_url:
            continue
        items.append(
            AudioItem(
                title=title,
                audio_url=audio_url,
                duration_sec=duration_sec,
                link=link,
            )
        )
    return items


def title_similarity(left: str, right: str) -> float:
    left_norm = normalize_title(left)
    right_norm = normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.94
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def build_audio_index(episodes: List[Dict[str, object]], rss_items: List[AudioItem]) -> Dict[str, Dict[str, object]]:
    audio_index: Dict[str, Dict[str, object]] = {}
    remaining = list(rss_items)

    for episode in episodes:
        title = str(episode["title"])
        best_item = None
        best_score = 0.0
        for item in remaining:
            score = title_similarity(title, item.title)
            if score > best_score:
                best_score = score
                best_item = item
        if best_item and best_score >= 0.72:
            audio_index[str(episode["episode_id"])] = {
                "episode_title": title,
                "rss_title": best_item.title,
                "audio_url": best_item.audio_url,
                "duration_sec": best_item.duration_sec,
                "link": best_item.link,
                "match_score": round(best_score, 3),
            }
            remaining.remove(best_item)
    return audio_index


def save_json(path: pathlib.Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_json(path: pathlib.Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def download_audio_file(audio_url: str, output_path: pathlib.Path) -> pathlib.Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        audio_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36",
            "Referer": "https://www.lennysnewsletter.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        output_path.write_bytes(response.read())
    return output_path


def render_clip(source_audio_path: pathlib.Path, output_path: pathlib.Path, start_sec: int, end_sec: int) -> pathlib.Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(1, end_sec - start_sec)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_sec),
        "-t",
        str(duration),
        "-i",
        str(source_audio_path),
        "-vn",
        "-acodec",
        "copy",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        fallback_command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_sec),
            "-t",
            str(duration),
            "-i",
            str(source_audio_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-b:a",
            "128k",
            str(output_path),
        ]
        completed = subprocess.run(fallback_command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "ffmpeg failed to render clip")
    return output_path


def count_cached_audio(episodes_dir: pathlib.Path, clips_dir: pathlib.Path) -> Dict[str, int]:
    episode_count = len(list(episodes_dir.glob("*.mp3"))) if episodes_dir.exists() else 0
    clip_count = len(list(clips_dir.glob("*.mp3"))) if clips_dir.exists() else 0
    return {
        "downloaded_episode_count": episode_count,
        "rendered_clip_count": clip_count,
    }
