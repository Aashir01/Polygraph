"""
hooks/inject.py
Registered for UserPromptSubmit.

If the latest verdict exists and is not VERIFIED, prepends a short evidence
summary to the prompt context so the agent is aware of outstanding issues.

Outputs a JSON block to stdout that Bob merges into the prompt context.
Prints nothing (empty stdout) when the verdict is VERIFIED or missing.

Always exits 0.
"""

import json
import sys
from pathlib import Path

_PRIVATE_DIR = Path.home() / ".polygraph_private"
_LATEST_VERDICT = _PRIVATE_DIR / "latest_verdict.json"


def _load_verdict() -> dict | None:
    if not _LATEST_VERDICT.exists():
        return None
    try:
        return json.loads(_LATEST_VERDICT.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _build_summary(result: dict) -> str:
    verdict = result.get("verdict", "UNKNOWN")
    lines = [f"[Polygraph] Last verdict: **{verdict}**"]
    for check in result.get("checks", []):
        name = check.get("name", "?")
        ok = check.get("ok", False)
        if ok:
            continue
        icon = "⚠" if name in ("trace_behavior", "claim_check") else "✗"
        flags = check.get("flags", [])
        lines.append(f"  {icon} {name}: {flags}")
        if name == "independent_test_run":
            failed = check.get("failed", 0)
            lines.append(f"      {failed} test(s) fail with the original (baseline) assertions.")
    lines.append("Fix the issues before committing.  See .polygraph/report.md for details.")
    return "\n".join(lines)


def main() -> None:
    # Consume stdin (Bob sends the event payload)
    sys.stdin.read()

    result = _load_verdict()
    if result is None:
        sys.exit(0)

    verdict = result.get("verdict", "UNKNOWN")
    if verdict in ("VERIFIED", "SKIPPED"):
        sys.exit(0)

    summary = _build_summary(result)

    # Bob UserPromptSubmit hook can inject context by writing JSON to stdout.
    # Format: {"context": "...string appended to the prompt..."}
    payload = {"context": summary}
    print(json.dumps(payload))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"inject.py fatal: {exc}", file=sys.stderr)
