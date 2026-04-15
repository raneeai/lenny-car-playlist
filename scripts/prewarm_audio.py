import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.server import ensure_catalog, ensure_audio_index, prewarm_clips  # noqa: E402


def main() -> None:
    theme = sys.argv[1].strip().lower() if len(sys.argv) > 1 else None
    max_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    ensure_catalog(force=False)
    ensure_audio_index(force=False)
    result = prewarm_clips(ensure_catalog(force=False)["clips"], theme=theme, max_clips=max_clips)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
