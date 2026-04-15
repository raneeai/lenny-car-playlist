from __future__ import annotations

import math
import random
import re
import uuid
from typing import Dict, List, Tuple

from app.themes import DEFAULT_THEME, THEMES


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", value.lower())


def parse_query(query: str) -> Dict[str, object]:
    normalized = normalize_text(query)
    selected_theme = DEFAULT_THEME
    selected_score = -1
    for theme, config in THEMES.items():
        score = sum(normalized.count(keyword) for keyword in config["keywords"])
        if theme in normalized:
            score += 4
        if score > selected_score:
            selected_score = score
            selected_theme = theme

    duration_minutes = 18
    if "10" in normalized or "quick" in normalized or "short" in normalized:
        duration_minutes = 12
    elif "20" in normalized or "deep" in normalized or "long" in normalized:
        duration_minutes = 22

    stop_words = {
        "hi",
        "lenny",
        "give",
        "me",
        "about",
        "clips",
        "clip",
        "podcast",
        "play",
        "playlist",
        "on",
        "for",
        "the",
        "and",
        "driving",
        "commute",
    }
    theme_keywords = set(THEMES[selected_theme]["keywords"])
    words = [
        word
        for word in normalized.split()
        if len(word) > 2 and word not in stop_words and word not in theme_keywords
    ]
    subtopic = " ".join(words[:3]) if words else selected_theme
    return {
        "intent": "start_playlist",
        "theme": selected_theme,
        "subtopic": subtopic,
        "duration_minutes": duration_minutes,
    }


def clip_query_score(clip: Dict[str, object], parsed_query: Dict[str, object], normalized_query: str) -> float:
    text = normalize_text(
        "%s %s %s %s"
        % (
            clip.get("summary_short", ""),
            clip.get("transcript_excerpt", ""),
            clip.get("episode_title", ""),
            clip.get("guest", ""),
        )
    )
    theme_bonus = 8 if clip["theme"] == parsed_query["theme"] else 0
    keyword_hits = sum(1 for word in normalized_query.split() if word and word in text)
    freshness_bonus = 1 if "2026" in str(clip.get("episode_title", "")) else 0
    return float(clip["score"]) + theme_bonus + keyword_hits + freshness_bonus


def build_playlist(query: str, clips: List[Dict[str, object]]) -> Dict[str, object]:
    parsed = parse_query(query)
    normalized_query = normalize_text(query)
    ranked = sorted(
        clips,
        key=lambda clip: clip_query_score(clip, parsed, normalized_query),
        reverse=True,
    )
    theme_ranked = [clip for clip in ranked if clip["theme"] == parsed["theme"]]
    if len(theme_ranked) >= 4:
        ranked = theme_ranked

    target_sec = parsed["duration_minutes"] * 60
    min_target_sec = max(600, target_sec - 180)
    max_target_sec = min(1500, target_sec + 180)
    chosen: List[Dict[str, object]] = []
    used_episodes: Dict[str, int] = {}
    used_ranges: List[Tuple[str, int, int]] = []
    total_sec = 0

    for clip in ranked:
        episode_count = used_episodes.get(clip["episode_id"], 0)
        if episode_count >= 2:
            continue
        overlaps = any(
            clip["episode_id"] == episode_id
            and not (clip["end_sec"] <= start_sec or clip["start_sec"] >= end_sec)
            for episode_id, start_sec, end_sec in used_ranges
        )
        if overlaps:
            continue
        if total_sec + int(clip["duration_sec"]) > max_target_sec and total_sec >= min_target_sec:
            continue
        chosen.append(clip)
        used_episodes[clip["episode_id"]] = episode_count + 1
        used_ranges.append((clip["episode_id"], int(clip["start_sec"]), int(clip["end_sec"])))
        total_sec += int(clip["duration_sec"])
        if len(chosen) >= 8 and total_sec >= min_target_sec:
            break

    if not chosen:
        chosen = ranked[:6]
        total_sec = sum(int(clip["duration_sec"]) for clip in chosen)

    wrap_up = (
        "That was the best of %s on %s. Next time, try %s."
        % (
            THEMES[parsed["theme"]]["label"],
            parsed["subtopic"],
            random.choice([theme for theme in THEMES if theme != parsed["theme"]]),
        )
    )
    return {
        "playlist_id": "pl_%s" % uuid.uuid4().hex[:10],
        "query": query,
        "theme": parsed["theme"],
        "subtopic": parsed["subtopic"],
        "duration_target_sec": target_sec,
        "duration_actual_sec": total_sec,
        "intro_text": "I curated %s original clips on %s. Starting playlist now."
        % (len(chosen), parsed["subtopic"]),
        "wrap_up_text": wrap_up,
        "items": [
            {
                "position": index + 1,
                "clip_id": clip["clip_id"],
                "episode_id": clip["episode_id"],
                "episode_title": clip["episode_title"],
                "guest": clip["guest"],
                "theme": clip["theme"],
                "start_sec": clip["start_sec"],
                "end_sec": clip["end_sec"],
                "duration_sec": clip["duration_sec"],
                "summary_short": clip["summary_short"],
                "transcript_excerpt": clip["transcript_excerpt"],
                "audio_status": "unresolved",
                "audio_url": None,
            }
            for index, clip in enumerate(chosen)
        ],
    }


def apply_command(command: str, playlist: Dict[str, object], current_position: int) -> Dict[str, object]:
    command_value = normalize_text(command).strip()
    items = playlist.get("items", [])
    if not items:
        return {"position": 0, "message": "No active playlist."}

    new_position = current_position
    if "next" in command_value:
        new_position = min(len(items) - 1, current_position + 1)
    elif "previous" in command_value:
        new_position = max(0, current_position - 1)
    elif "repeat" in command_value:
        new_position = current_position
    elif "stop" in command_value:
        return {"position": current_position, "message": "Playback stopped."}
    elif "explain" in command_value:
        item = items[current_position]
        excerpt = item["transcript_excerpt"][:280].strip()
        return {
            "position": current_position,
            "message": "Here is a deeper explanation: %s%s"
            % (excerpt, "..." if len(item["transcript_excerpt"]) > 280 else ""),
        }
    elif "change topic" in command_value:
        return {
            "position": current_position,
            "message": "Change topic requested. Start a new playlist query.",
        }

    current_item = items[new_position]
    return {
        "position": new_position,
        "message": "Now on clip %s: %s"
        % (new_position + 1, current_item["summary_short"]),
    }
