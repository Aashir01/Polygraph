"""
hooks/dump_event.py
Reads a JSON event from stdin and appends it (with a timestamp) to
~/.polygraph_private/raw_events.jsonl, creating the folder if missing.

Registered in .bob/settings.json for all five Bob lifecycle events.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {"raw": raw}

    event["_ts"] = datetime.now(timezone.utc).isoformat()

    output_dir = Path.home() / ".polygraph_private"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "raw_events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
