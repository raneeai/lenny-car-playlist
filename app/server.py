from __future__ import annotations

import json
import pathlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from app.ingest import build_catalog
from app.playlist import apply_command, build_playlist
from app.themes import THEMES

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_SOURCE_DIR = ROOT / "data-source"
CACHE_DIR = ROOT / "data"
CATALOG_PATH = CACHE_DIR / "catalog.json"

STATE: Dict[str, Any] = {
    "catalog": None,
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
        if parsed.path == "/api/health":
            catalog = ensure_catalog(force=False)
            self._send_json(
                {
                    "ok": True,
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
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
            self._send_json(
                {
                    "generated_at": catalog["generated_at"],
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
                    "theme_clip_counts": catalog["theme_clip_counts"],
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
            self._send_json(
                {
                    "ok": True,
                    "episode_count": catalog["episode_count"],
                    "clip_count": catalog["clip_count"],
                    "theme_clip_counts": catalog["theme_clip_counts"],
                }
            )
            return

        if parsed.path == "/api/playlists":
            query = str(payload.get("query", "")).strip()
            if not query:
                self._send_json({"error": "Missing query"}, status=400)
                return
            catalog = ensure_catalog(force=False)
            playlist = build_playlist(query, catalog["clips"])
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
