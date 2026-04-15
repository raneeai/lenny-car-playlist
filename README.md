# lenny-car-playlists

**Your personal Executive Assistant for Lenny's content.**

Say **"Hi Lenny"** while driving to instantly receive hand-curated playlists made entirely from **original Lenny podcast clips** with **no TTS, only original audio**.

Focused on the highest-value topics:

- Product Management
- Growth
- AI
- Productivity

Built specifically for busy North American product leaders, Heads of Product, and founders who love Lenny's content but do not have time to listen to full episodes.

## Local MVP

This repo contains a local-testable MVP prototype for `Lenny Executive Clips`.

## What works now

- ingests the public `lennys-newsletterpodcastdata` repo
- parses 50 podcast transcripts
- creates clip candidates across the 6 MVP themes
- builds playlists for prompts like `Growth cold start clips`
- exposes a local JSON API with no third-party Python dependencies
- resolves official podcast audio URLs from the Substack RSS feed
- downloads source episode audio locally
- renders clip-level audio with `ffmpeg`
- serves playable local audio files
- serves a local web UI for playlist generation and playback at `/`
- supports installable PWA metadata and offline app-shell caching

## What is not finished yet

- automatic bulk audio download and clip prewarming
- mobile UI / PWA
- on-device speech-to-text
- stronger title matching fallbacks for the full archive

The current prototype proves the content understanding and playlist generation layer first.

## Run locally

```bash
cd /Users/zhangyunfan/Downloads/codex
python3 scripts/run_server.py
```

If port `8000` is busy:

```bash
python3 scripts/run_server.py 8001
```

Then open these endpoints:

- `GET http://127.0.0.1:8000/`
- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/themes`
- `GET http://127.0.0.1:8000/api/catalog`

Create a playlist:

```bash
curl -X POST http://127.0.0.1:8000/api/playlists \
  -H 'Content-Type: application/json' \
  -d '{"query":"Hi Lenny, I am driving. Give me growth cold start clips"}'
```

Send a command:

```bash
curl -X POST http://127.0.0.1:8000/api/commands \
  -H 'Content-Type: application/json' \
  -d '{"command":"Explain more"}'
```

Force a fresh ingest:

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/sync
```

Sync official audio mappings:

```bash
curl -X POST http://127.0.0.1:8000/api/audio/sync
```

Download one episode's source audio:

```bash
curl -X POST http://127.0.0.1:8000/api/audio/download \
  -H 'Content-Type: application/json' \
  -d '{"episode_id":"amol-avasare"}'
```

Render one clip into a playable mp3:

```bash
curl -X POST http://127.0.0.1:8000/api/audio/render \
  -H 'Content-Type: application/json' \
  -d '{"clip_id":"amol-avasare-2836-2961"}'
```

Then open the returned `audio_url`, for example:

```bash
http://127.0.0.1:8000/audio/clips/amol-avasare-2836-2961.mp3
```

## Fastest demo flow

1. Start the server
2. Open `http://127.0.0.1:8000/`
3. Click a prompt chip or enter your own query
4. Click `Generate playlist`
5. Click `Prepare playable audio`
6. Press `Play` on any prepared clip

## PWA notes

- the app exposes `manifest.webmanifest`
- the browser registers a local service worker from `/sw.js`
- the current PWA layer caches the app shell for faster reloads and installability
- playlist data and audio files are still fetched live from the local server

## Project layout

- `app/ingest.py`: transcript parsing and clip candidate generation
- `app/playlist.py`: query understanding and playlist assembly
- `app/audio.py`: RSS audio resolution, download, and clip rendering
- `app/server.py`: local HTTP API
- `data-source/`: public Lenny data repo
- `data/catalog.json`: generated local catalog cache
