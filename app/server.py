from __future__ import annotations

import json
import mimetypes
import pathlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from app.audio import (
    RSS_URL,
    build_audio_index,
    count_cached_audio,
    download_audio_file,
    fetch_rss_xml,
    load_json,
    parse_rss_items,
    render_clip,
    save_json,
)
from app.ingest import build_catalog
from app.playlist import apply_command, build_playlist
from app.themes import THEMES

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_SOURCE_DIR = ROOT / "data-source"
CACHE_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
CATALOG_PATH = CACHE_DIR / "catalog.json"
AUDIO_INDEX_PATH = CACHE_DIR / "audio_index.json"
AUDIO_EPISODES_DIR = CACHE_DIR / "audio" / "episodes"
AUDIO_CLIPS_DIR = CACHE_DIR / "audio" / "clips"

STATE: Dict[str, Any] = {
    "catalog": None,
    "audio_index": None,
    "last_playlist": None,
    "current_position": 0,
}


def ensure_catalog(force: bool = False) -> Dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if force or not CATALOG_PATH.exists():
        catalog = build_catalog(DATA_SOURCE_DIR)
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2))
        STATE["catalog"] = catalog
        return catalog
    if STATE["catalog"] is None:
        STATE["catalog"] = json.loads(CATALOG_PATH.read_text())
    return STATE["catalog"]


def ensure_audio_index(force: bool = False) -> Dict[str, Any]:
    if force or not AUDIO_INDEX_PATH.exists():
        try:
            catalog = ensure_catalog(force=False)
            xml_text = fetch_rss_xml(RSS_URL)
            rss_items = parse_rss_items(xml_text)
            audio_index = build_audio_index(catalog["episodes"], rss_items)
            save_json(AUDIO_INDEX_PATH, audio_index)
            STATE["audio_index"] = audio_index
            return audio_index
        except Exception:
            STATE["audio_index"] = {}
            return {}
    if STATE["audio_index"] is None:
        STATE["audio_index"] = load_json(AUDIO_INDEX_PATH)
    return STATE["audio_index"]


def annotate_playlist_with_audio(playlist: Dict[str, Any]) -> Dict[str, Any]:
    audio_index = ensure_audio_index(force=False)
    for item in playlist.get("items", []):
        audio_meta = audio_index.get(item["episode_id"])
        if audio_meta:
            source_path = AUDIO_EPISODES_DIR / ("%s.mp3" % item["episode_id"])
            clip_path = AUDIO_CLIPS_DIR / ("%s.mp3" % item["clip_id"])
            item["source_audio_url"] = audio_meta["audio_url"]
            item["audio_status"] = "source_available"
            if clip_path.exists():
                item["audio_url"] = "/audio/clips/%s.mp3" % item["clip_id"]
                item["audio_status"] = "clip_ready"
            elif source_path.exists():
                item["audio_status"] = "source_downloaded"
                item["audio_local_path"] = str(source_path)
        else:
            item["source_audio_url"] = None
    return playlist


def send_file(handler: BaseHTTPRequestHandler, file_path: pathlib.Path) -> None:
    if not file_path.exists() or not file_path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND)
        return
    content = file_path.read_bytes()
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(content)


def prepare_playlist_audio(playlist: Dict[str, Any]) -> Dict[str, Any]:
    audio_index = ensure_audio_index(force=False)
    prepared = 0
    skipped = 0
    errors = []
    for item in playlist.get("items", []):
        audio_meta = audio_index.get(item["episode_id"])
        if not audio_meta:
            skipped += 1
            continue
        try:
            source_path = AUDIO_EPISODES_DIR / ("%s.mp3" % item["episode_id"])
            if not source_path.exists():
                download_audio_file(audio_meta["audio_url"], source_path)
            clip_path = AUDIO_CLIPS_DIR / ("%s.mp3" % item["clip_id"])
            if not clip_path.exists():
                render_clip(
                    source_path,
                    clip_path,
                    int(item["start_sec"]),
                    int(item["end_sec"]),
                )
            prepared += 1
        except Exception as exc:
            errors.append({"clip_id": item["clip_id"], "error": str(exc)})
    annotate_playlist_with_audio(playlist)
    return {
        "prepared": prepared,
        "skipped": skipped,
        "errors": errors,
        "playlist": playlist,
    }


def prewarm_clips(
    clips: list[Dict[str, Any]],
    *,
    theme: str | None = None,
    max_clips: int = 12,
) -> Dict[str, Any]:
    audio_index = ensure_audio_index(force=False)
    selected = clips
    if theme:
        selected = [clip for clip in selected if clip["theme"] == theme]
    selected = selected[:max_clips]

    prepared = 0
    skipped = 0
    errors = []
    downloaded_episodes = set()

    for clip in selected:
        audio_meta = audio_index.get(clip["episode_id"])
        if not audio_meta:
            skipped += 1
            continue
        try:
            source_path = AUDIO_EPISODES_DIR / ("%s.mp3" % clip["episode_id"])
            if not source_path.exists():
                download_audio_file(audio_meta["audio_url"], source_path)
                downloaded_episodes.add(clip["episode_id"])
            clip_path = AUDIO_CLIPS_DIR / ("%s.mp3" % clip["clip_id"])
            if not clip_path.exists():
                render_clip(
                    source_path,
                    clip_path,
                    int(clip["start_sec"]),
                    int(clip["end_sec"]),
                )
            prepared += 1
        except Exception as exc:
            errors.append({"clip_id": clip["clip_id"], "error": str(exc)})

    cache_stats = count_cached_audio(AUDIO_EPISODES_DIR, AUDIO_CLIPS_DIR)
    return {
        "requested_theme": theme,
        "requested_clip_count": len(selected),
        "prepared": prepared,
        "skipped": skipped,
        "newly_downloaded_episode_count": len(downloaded_episodes),
        "errors": errors,
        **cache_stats,
    }


class LennyHandler(BaseHTTPRequestHandler):
    server_version = "LennyExecutiveClips/0.1"

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True}, status=200)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            send_file(self, WEB_DIR / "index.html")
            return
        if parsed.path == "/manifest.webmanifest":
            send_file(self, WEB_DIR / "manifest.webmanifest")
            return
        if parsed.path == "/sw.js":
            send_file(self, WEB_DIR / "sw.js")
            return
        if parsed.path == "/icon.svg":
            send_file(self, WEB_DIR / "icon.svg")
            return
        if parsed.path.startswith("/web/"):
            asset_name = parsed.path.replace("/web/", "", 1)
            send_file(self, WEB_DIR / asset_name)
            return
        if parsed.path.startswith("/audio/clips/"):
            clip_name = pathlib.Path(parsed.path).name
            send_file(self, AUDIO_CLIPS_DIR / clip_name)
            return
        if parsed.path.startswith("/audio/episodes/"):
            episode_name = pathlib.Path(parsed.path).name
            send_file(self, AUDIO_EPISODES_DIR / episode_name)
            return
        if parsed.path == "/api/health":
            catalog = ensure_catalog(force=False)
            audio_index = ensure_audio_index(force=False)
            cache_stats = count_cached_audio(AUDIO_EPISODES_DIR, AUDIO_CLIPS_DIR)
            self._send_json(
                {
                    "ok": True,
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
                    "audio_episode_count": len(audio_index),
                    **cache_stats,
                }
            )
            return
        if parsed.path == "/api/themes":
            self._send_json(
                {
                    "themes": [
                        {"id": key, "label": value["label"], "keywords": value["keywords"]}
                        for key, value in THEMES.items()
                    ]
                }
            )
            return
        if parsed.path == "/api/catalog":
            catalog = ensure_catalog(force=False)
            top_clips = catalog["clips"][:12]
            audio_index = ensure_audio_index(force=False)
            self._send_json(
                {
                    "generated_at": catalog["generated_at"],
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
                    "theme_clip_counts": catalog["theme_clip_counts"],
                    "audio_episode_count": len(audio_index),
                    "top_clips": top_clips,
                }
            )
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()

        if parsed.path == "/api/ingest/sync":
            catalog = ensure_catalog(force=True)
            audio_index = ensure_audio_index(force=True)
            self._send_json(
                {
                    "ok": True,
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
                    "theme_clip_counts": catalog["theme_clip_counts"],
                    "audio_episode_count": len(audio_index),
                }
            )
            return

        if parsed.path == "/api/audio/sync":
            audio_index = ensure_audio_index(force=True)
            cache_stats = count_cached_audio(AUDIO_EPISODES_DIR, AUDIO_CLIPS_DIR)
            self._send_json(
                {
                    "ok": True,
                    "audio_episode_count": len(audio_index),
                    "sample_matches": list(audio_index.items())[:5],
                    **cache_stats,
                }
            )
            return

        if parsed.path == "/api/audio/prewarm":
            catalog = ensure_catalog(force=False)
            theme = str(payload.get("theme", "")).strip().lower() or None
            max_clips = int(payload.get("max_clips", 12))
            max_clips = max(1, min(max_clips, 30))
            result = prewarm_clips(catalog["clips"], theme=theme, max_clips=max_clips)
            self._send_json({"ok": True, **result})
            return

        if parsed.path == "/api/audio/download":
            episode_id = str(payload.get("episode_id", "")).strip()
            if not episode_id:
                self._send_json({"error": "Missing episode_id"}, status=400)
                return
            audio_index = ensure_audio_index(force=False)
            audio_meta = audio_index.get(episode_id)
            if not audio_meta:
                self._send_json({"error": "No audio mapping for episode"}, status=404)
                return
            output_path = AUDIO_EPISODES_DIR / ("%s.mp3" % episode_id)
            download_audio_file(audio_meta["audio_url"], output_path)
            self._send_json(
                {
                    "ok": True,
                    "episode_id": episode_id,
                    "audio_url": "/audio/episodes/%s.mp3" % episode_id,
                    "audio_local_path": str(output_path),
                }
            )
            return

        if parsed.path == "/api/audio/render":
            clip_id = str(payload.get("clip_id", "")).strip()
            if not clip_id:
                self._send_json({"error": "Missing clip_id"}, status=400)
                return
            catalog = ensure_catalog(force=False)
            clip = next((item for item in catalog["clips"] if item["clip_id"] == clip_id), None)
            if not clip:
                self._send_json({"error": "Unknown clip_id"}, status=404)
                return
            source_path = AUDIO_EPISODES_DIR / ("%s.mp3" % clip["episode_id"])
            if not source_path.exists():
                self._send_json(
                    {
                        "error": "Episode audio not downloaded",
                        "episode_id": clip["episode_id"],
                    },
                    status=400,
                )
                return
            output_path = AUDIO_CLIPS_DIR / ("%s.mp3" % clip_id)
            render_clip(
                source_path,
                output_path,
                int(clip["start_sec"]),
                int(clip["end_sec"]),
            )
            self._send_json(
                {
                    "ok": True,
                    "clip_id": clip_id,
                    "audio_url": "/audio/clips/%s.mp3" % clip_id,
                    "audio_local_path": str(output_path),
                }
            )
            return

        if parsed.path == "/api/playlists/prepare":
            playlist = STATE.get("last_playlist")
            if not playlist:
                self._send_json({"error": "No active playlist"}, status=400)
                return
            result = prepare_playlist_audio(playlist)
            STATE["last_playlist"] = result["playlist"]
            self._send_json(result)
            return

        if parsed.path == "/api/playlists":
            query = str(payload.get("query", "")).strip()
            if not query:
                self._send_json({"error": "Missing query"}, status=400)
                return
            catalog = ensure_catalog(force=False)
            playlist = build_playlist(query, catalog["clips"])
            playlist = annotate_playlist_with_audio(playlist)
            STATE["last_playlist"] = playlist
            STATE["current_position"] = 0
            self._send_json(playlist)
            return

        if parsed.path == "/api/commands":
            command = str(payload.get("command", "")).strip()
            playlist = STATE.get("last_playlist")
            if not playlist:
                self._send_json({"error": "No active playlist"}, status=400)
                return
            result = apply_command(command, playlist, int(STATE["current_position"]))
            STATE["current_position"] = int(result["position"])
            self._send_json(result)
            return

        self._send_json({"error": "Not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    ensure_catalog(force=False)
    server = ThreadingHTTPServer((host, port), LennyHandler)
    print("Lenny Executive Clips server running at http://%s:%s" % (host, port))
    server.serve_forever()


if __name__ == "__main__":
    run_server()
