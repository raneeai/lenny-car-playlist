# Lenny Executive Clips - Execution Backlog

## Delivery Principle

Backlog is organized around the fastest path to a local-testable MVP, not around ideal long-term platform design.

## Milestone 0 - Decision Lock

Goal: remove ambiguity before coding the core engine.

### Tickets

- `ARCH-001` Lock v0 client to `PWA first`, not React Native
- `ARCH-002` Lock v0 backend to `FastAPI + SQLite + Chroma + ffmpeg`
- `DATA-001` Decide starter-pack-first vs paid-archive-first
- `DATA-002` Confirm official podcast audio source and allowed local caching path
- `UX-001` Freeze the 6-theme taxonomy and initial subtopics
- `UX-002` Freeze the v0 command set and response copy

### Exit criteria

- one stack chosen
- one data path chosen
- one MVP interaction model chosen

## Milestone 1 - Content Ingestion

Goal: get Lenny data into a normalized local store.

### Tickets

- `DATA-101` Clone or download the `lennysdata` starter pack
- `DATA-102` Parse `index.json` into normalized episode/newsletter records
- `DATA-103` Parse podcast markdown frontmatter and transcript body
- `DATA-104` Build transcript segment parser from timestamped speaker text
- `DATA-105` Create SQLite schema for episodes, segments, themes, clips, playlists
- `DATA-106` Add ingestion idempotency and file hashing
- `DATA-107` Build local admin report for ingest status and failures

### Exit criteria

- 50 starter episodes loaded
- transcript segments queryable locally
- ingest can be rerun safely

## Milestone 2 - Audio Resolution and Caching

Goal: join transcript data with playable original audio.

### Tickets

- `AUDIO-201` Discover official RSS / audio feed items
- `AUDIO-202` Implement fuzzy title match between transcript title and audio item
- `AUDIO-203` Add manual override file for mismatched episodes
- `AUDIO-204` Download and cache selected episode audio locally
- `AUDIO-205` Extract episode duration and validate audio integrity
- `AUDIO-206` Build a small audio inventory dashboard

### Exit criteria

- at least 10-20 strong episodes have verified local audio
- each mapped episode has transcript + audio + duration

## Milestone 3 - Theme and Clip Candidate Generation

Goal: create a reusable library of high-quality clip candidates.

### Tickets

- `ML-301` Define keyword/embedding seed set for 6 themes
- `ML-302` Auto-tag transcript segments to theme candidates
- `ML-303` Implement transcript windowing into 60-180 second candidates
- `ML-304` Add clip scoring for actionability, coherence, and theme fit
- `ML-305` Remove overlap and duplicate ideas
- `ML-306` Generate short on-screen summaries for each clip
- `ML-307` Build curator review CSV or JSON export
- `OPS-301` Hand-review the first 50-100 clips for quality

### Exit criteria

- at least 50 demo-quality clips available
- each clip has theme, timestamps, summary, and audio source

## Milestone 4 - Playlist Composer

Goal: turn a query into a coherent 10-25 minute listening experience.

### Tickets

- `CORE-401` Build query parser for theme + subtopic extraction
- `CORE-402` Add query normalization for variants like `cold start`, `prioritization`, `hiring`
- `CORE-403` Rank candidate clips using semantic similarity + quality score
- `CORE-404` Add diversity rules to avoid too many clips from one episode
- `CORE-405` Add duration packing logic for 10-25 minute targets
- `CORE-406` Create playlist/session schema
- `CORE-407` Implement `Explain more` fallback logic
- `CORE-408` Return playlist summaries and wrap-up text

### Exit criteria

- queries like `Growth cold start clips` produce a valid playlist
- result is coherent, non-repetitive, and within duration bounds

## Milestone 5 - Clip Rendering

Goal: make every playlist item immediately playable.

### Tickets

- `AUDIO-501` Build ffmpeg clip extraction worker
- `AUDIO-502` Support precomputed clips and lazy clip generation
- `AUDIO-503` Normalize output loudness if needed
- `AUDIO-504` Cache rendered clip files by stable hash
- `AUDIO-505` Add failed-render retry and logging

### Exit criteria

- playlist items resolve to local playable audio URLs
- clip render time is not on the critical path for common queries

## Milestone 6 - API Layer

Goal: expose a simple local backend the client can talk to.

### Tickets

- `API-601` Create FastAPI project structure
- `API-602` Add `POST /api/playlists`
- `API-603` Add `POST /api/commands`
- `API-604` Add `GET /api/themes`
- `API-605` Add `POST /api/ingest/sync`
- `API-606` Add healthcheck and startup diagnostics
- `API-607` Add structured logs and request timing

### Exit criteria

- client can request and control playlists end-to-end

## Milestone 7 - Client App

Goal: make the core driving flow testable in a browser on laptop or phone.

### Tickets

- `WEB-701` Scaffold PWA shell
- `WEB-702` Build `Hi Lenny` input surface with microphone button
- `WEB-703` Build now playing screen
- `WEB-704` Build queue and progress UI
- `WEB-705` Build executive summary card
- `WEB-706` Implement command buttons for `Next / Previous / Repeat / Stop / Change topic / Explain more`
- `WEB-707` Add mobile-safe responsive layout
- `WEB-708` Add offline-ready local cache behavior for current playlist

### Exit criteria

- a user can request a topic and listen through a playlist locally

## Milestone 8 - Voice and Driving Constraints

Goal: get close to the intended interaction model without overengineering.

### Tickets

- `VOICE-801` Add push-to-talk STT with faster-whisper
- `VOICE-802` Parse command intents separately from content queries
- `VOICE-803` Add noisy-environment testing with sample recordings
- `VOICE-804` Add short confirmation copy without TTS dependency
- `VOICE-805` Evaluate wake-word feasibility after push-to-talk works

### Exit criteria

- core flow works with spoken input
- no wake-word dependency for demo success

## Milestone 9 - Quality and Telemetry

Goal: measure whether the magic is actually working.

### Tickets

- `OBS-901` Log time-to-first-audio
- `OBS-902` Log playlist completion
- `OBS-903` Log skip rate per clip
- `OBS-904` Log top requested themes/subtopics
- `QA-901` Build a manual scorecard for clip and playlist quality
- `QA-902` Add regression tests for transcript parsing and playlist packing
- `QA-903` Add smoke test for playback API

### Exit criteria

- basic usage metrics visible locally
- parsing and playlist generation protected by tests

## Suggested 10-Day Sprint Cut

If the ask is `make something testable immediately`, this is the smallest useful slice:

### Day 1

- `ARCH-001`
- `ARCH-002`
- `DATA-101`
- `DATA-102`
- `DATA-103`

### Day 2

- `DATA-104`
- `DATA-105`
- `AUDIO-201`
- `AUDIO-202`

### Day 3

- `AUDIO-203`
- `AUDIO-204`
- `AUDIO-205`

### Day 4

- `ML-301`
- `ML-302`
- `ML-303`

### Day 5

- `ML-304`
- `ML-305`
- `ML-306`

### Day 6

- `CORE-401`
- `CORE-402`
- `CORE-403`

### Day 7

- `CORE-404`
- `CORE-405`
- `CORE-406`

### Day 8

- `AUDIO-501`
- `AUDIO-504`
- `API-601`
- `API-602`

### Day 9

- `WEB-701`
- `WEB-702`
- `WEB-703`
- `WEB-706`

### Day 10

- `WEB-705`
- `VOICE-801`
- `OBS-901`
- `QA-903`

## What To De-Scope First If Time Breaks

Cut in this order:

1. true wake word
2. React Native
3. dynamic clip generation at request time
4. newsletter integration
5. advanced explain-more behavior

Do not cut:

1. transcript + audio join
2. precomputed clips
3. playlist quality rules
4. startup speed
5. simple but solid player UI

## Immediate Next 5 Tickets

If we were starting implementation right now, I would open these first:

1. `DATA-101` Clone/download the public starter pack and lock the ingest path
2. `DATA-104` Build the transcript parser
3. `AUDIO-201` Resolve the official podcast audio feed
4. `ML-303` Create first-pass clip candidate extraction
5. `API-602` Return a hardcoded playlist from real data end-to-end

## Sources

- [Lenny's Data](https://www.lennysdata.com/)
- [Public starter repo](https://github.com/LennysNewsletter/lennys-newsletterpodcastdata)
- [Starter repo raw index](https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/index.json)
