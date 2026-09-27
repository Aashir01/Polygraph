"""
hooks/gate.py
Registered for PreToolUse on the execute_command tool (matcher: git commit|push|gh pr).

If the command contains "git commit", "git push", or "gh pr create" AND
git status shows changes under demo_repo/, the verdict engine is run.

Exit codes:
  0 — command is allowed to proceed (or gate is bypassed)
  2 — command is BLOCKED (verdict is not VERIFIED)

Bypassed when either of these files exists:
  ~/.polygraph_private/GATE_OFF
  ~/.polygraph_private/override

Always exits 0 on unexpected errors (fail-open).
"""

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_PRIVATE_DIR = Path.home() / ".polygraph_private"
_GATE_OFF = _PRIVATE_DIR / "GATE_OFF"
_OVERRIDE = _PRIVATE_DIR / "override"
_TRACE = _PRIVATE_DIR / "trace.jsonl"
_GENESIS = "0" * 64

_TRIGGER_RE = re.compile(r"git\s+(commit|push)\b|gh\s+pr\s+create")


def _demo_repo_has_changes(cwd: str) -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain", "demo_repo/"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return bool(r.stdout.strip())


def _append_gate_block(command: str, verdict: str, session_id: str = "") -> None:
    """Write a GATE_BLOCK entry into the hash-chained trace."""
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    last_hash = _GENESIS
    if _TRACE.exists():
        last_line = ""
        with open(_TRACE, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if last_line:
            try:
                last_hash = json.loads(last_line).get("hash", _GENESIS)
            except json.JSONDecodeError:
                pass

    entry: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "tool_name": "gate",
        "category": "GATE_BLOCK",
        "target": command,
        "file_sha256": None,
        "blocked_verdict": verdict,
        "prev_hash": last_hash,
    }
    entry_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    entry["hash"] = hashlib.sha256((last_hash + entry_json).encode()).hexdigest()
    with open(_TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {}

    command: str = (event.get("tool_input") or {}).get("command", "")
    cwd: str = event.get("cwd", ".")
    session_id: str = event.get("session_id", "")

    # Only act on commit/push/pr commands
    if not _TRIGGER_RE.search(command):
        sys.exit(0)

    # Only act when demo_repo/ has uncommitted changes
    if not _demo_repo_has_changes(cwd):
        sys.exit(0)

    # Bypass flags
    if _GATE_OFF.exists() or _OVERRIDE.exists():
        # Still run verdict for the record but don't block
        try:
            from polygraph.verdict import run_verdict
            result = run_verdict()
            try:
                from polygraph.run_recorder import record_verdict
                record_verdict(result, gate_block=False)
            except Exception as exc:  # noqa: BLE001
                print(f"[polygraph/gate] run_recorder error: {exc}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"[polygraph/gate] verdict error (bypass active): {exc}", file=sys.stderr)
        sys.exit(0)

    # Run verdict
    try:
        from polygraph.verdict import run_verdict
        result = run_verdict()
    except Exception as exc:  # noqa: BLE001
        print(f"[polygraph/gate] verdict engine error: {exc}", file=sys.stderr)
        sys.exit(0)  # fail-open on engine crash

    verdict = result.get("verdict", "UNKNOWN")

    if verdict == "VERIFIED":
        # Record the successful verdict
        try:
            from polygraph.run_recorder import record_verdict
            record_verdict(result, gate_block=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[polygraph/gate] run_recorder error: {exc}", file=sys.stderr)
        sys.exit(0)

    # Block — write GATE_BLOCK trace entry first
    try:
        _append_gate_block(command, verdict, session_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[polygraph/gate] GATE_BLOCK trace write error: {exc}", file=sys.stderr)

    # Record block event in run recorder
    try:
        from polygraph.run_recorder import record_verdict
        record_verdict(result, gate_block=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[polygraph/gate] run_recorder error: {exc}", file=sys.stderr)

    # Build a human-readable block message
    lines = [
        "╔══════════════════════════════════════════════════════╗",
        f"║  POLYGRAPH GATE — BLOCKED ({verdict})",
        "╠══════════════════════════════════════════════════════╣",
    ]
    for check in result.get("checks", []):
        name = check.get("name", "?")
        ok = check.get("ok", False)
        icon = "✓" if ok else "✗"
        flags = check.get("flags", [])
        lines.append(f"║  {icon} {name}" + (f"  →  {flags}" if flags and not ok else ""))

        if name == "independent_test_run" and not ok:
            failed = check.get("failed", 0)
            lines.append(f"║      {failed} test(s) failed with original assertions")

        if name == "claim_check":
            for s in check.get("sentences", []):
                if s["verdict"] == "NOT_SUPPORTED":
                    lines.append(f"║      ✗ NOT SUPPORTED: {s['sentence'][:70]}")

    lines += [
        "╠══════════════════════════════════════════════════════╣",
        "║  Fix the issues above, then re-run the tests.",
        "║  See .polygraph/report.md for the full evidence card.",
        "╚══════════════════════════════════════════════════════╝",
    ]
    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"gate.py fatal: {exc}", file=sys.stderr)
