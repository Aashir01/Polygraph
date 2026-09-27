"""
hooks/record.py
Registered for all five Bob lifecycle events.

For PostToolUse events it appends a normalized, hash-chained entry to
~/.polygraph_private/trace.jsonl.

For all other events it still appends to raw_events.jsonl (unchanged
behaviour from the previous dump_event.py).

Always exits 0 (fail-open).
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------

# Tools whose primary effect is reading (not mutating) a file
_READ_TOOLS = {
    "read_file", "get_file", "glob", "grep",
    "list_files", "GetSymbolsOverview", "FindSymbol",
    "FindReferencingSymbols",
}

# Tools that write / mutate source files
_EDIT_TOOLS = {
    "write_file", "apply_diff", "search_and_replace", "insert_content",
    "office_edit",
}

_TEST_FILE_RE = re.compile(r"(^|[\\/])test_[^\\/]+\.py$|[\\/]tests[\\/]")


def _is_test_path(path: str) -> bool:
    return bool(_TEST_FILE_RE.search(path))


def _categorize(tool_name: str, tool_input: dict) -> tuple[str, str]:
    """Return (category, target) for a PostToolUse event."""
    path: str = tool_input.get("path", "")
    command: str = tool_input.get("command", "")

    if tool_name in _READ_TOOLS:
        return "READ", path or command

    if tool_name in _EDIT_TOOLS:
        if path and _is_test_path(path):
            return "EDIT_TEST", path
        return "EDIT_SRC", path

    if tool_name == "execute_command":
        cmd = command.strip()
        # pg_test or bare pytest invocation
        if re.search(r"\bpytest\b", cmd) or re.search(r"\bpg_test\b", cmd):
            return "RUN_TEST", cmd
        return "RUN_OTHER", cmd

    return "OTHER", path or command


# ---------------------------------------------------------------------------
# SHA-256 helpers
# ---------------------------------------------------------------------------

def _sha256_file(abs_path: str) -> str | None:
    """Return hex digest of the file contents, or None if unreadable."""
    try:
        return hashlib.sha256(Path(abs_path).read_bytes()).hexdigest()
    except OSError:
        return None


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Trace chain append
# ---------------------------------------------------------------------------

_PRIVATE_DIR = Path.home() / ".polygraph_private"
_TRACE = _PRIVATE_DIR / "trace.jsonl"
_RAW = _PRIVATE_DIR / "raw_events.jsonl"
_GENESIS = "0" * 64  # sentinel prev_hash for the first entry


def _last_hash() -> str:
    """Read the `hash` field of the last line in trace.jsonl."""
    if not _TRACE.exists():
        return _GENESIS
    last_line = ""
    with open(_TRACE, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return _GENESIS
    try:
        return json.loads(last_line).get("hash", _GENESIS)
    except json.JSONDecodeError:
        return _GENESIS


def _append_trace(entry: dict) -> None:
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    prev_hash = _last_hash()
    entry["prev_hash"] = prev_hash
    entry_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    entry["hash"] = _sha256_str(prev_hash + entry_json)
    with open(_TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _append_raw(event: dict) -> None:
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_RAW, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {"raw": raw}

    ts = datetime.now(timezone.utc).isoformat()
    event["_ts"] = ts
    _append_raw(event)

    if event.get("hook_event_name") != "PostToolUse":
        return

    tool_name: str = event.get("tool_name", "")
    tool_input: dict = event.get("tool_input") or {}
    cwd: str = event.get("cwd", "")

    category, target = _categorize(tool_name, tool_input)

    # Resolve file hash (best-effort; None for commands / missing files)
    file_hash: str | None = None
    if target and category in ("EDIT_SRC", "EDIT_TEST", "READ"):
        abs_path = target if Path(target).is_absolute() else str(Path(cwd) / target)
        file_hash = _sha256_file(abs_path)

    entry: dict = {
        "ts": ts,
        "session_id": event.get("session_id", ""),
        "tool_name": tool_name,
        "category": category,
        "target": target,
        "file_sha256": file_hash,
    }
    _append_trace(entry)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"record.py error: {exc}", file=sys.stderr)
