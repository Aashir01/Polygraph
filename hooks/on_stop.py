"""
hooks/on_stop.py
Registered for the Stop event.

Reads the Bob JSON payload from stdin, runs the Polygraph verdict engine
(only if demo_repo/ has changed from the baseline tag), and writes the
verdict artefacts.

Always exits 0 (fail-open per project policy).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {}

    try:
        from polygraph.verdict import run_verdict
        result = run_verdict(event)
        verdict = result.get("verdict", "UNKNOWN")
        print(f"[polygraph] verdict: {verdict}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[polygraph] on_stop.py error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"on_stop.py fatal: {exc}", file=sys.stderr)
