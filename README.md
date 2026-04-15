# Lenny Executive Clips - Local MVP

This repo contains a local-testable MVP prototype for `Lenny Executive Clips`.

## What works now

- ingests the public `lennys-newsletterpodcastdata` repo
- parses 50 podcast transcripts
- creates clip candidates across the 6 MVP themes
- builds playlists for prompts like `Growth cold start clips`
- exposes a local JSON API with no third-party Python dependencies

## What is not finished yet

- original audio URL resolution from the public podcast feed
- real clip extraction with `ffmpeg`
- mobile UI / PWA
- on-device speech-to-text

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

## Project layout

- `app/ingest.py`: transcript parsing and clip candidate generation
- `app/playlist.py`: query understanding and playlist assembly
- `app/server.py`: local HTTP API
- `data-source/`: public Lenny data repo
- `data/catalog.json`: generated local catalog cache

## Next step

Wire `AUDIO-201` and `AUDIO-204` from the backlog:

1. resolve official episode audio URLs
2. cache selected source files locally
3. clip with `ffmpeg`
4. return playable audio URLs instead of transcript-only items
