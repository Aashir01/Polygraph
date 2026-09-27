"""
polygraph/pg_test.py
A pytest wrapper that logs the test run into the Polygraph hash-chain
(~/.polygraph_private/trace.jsonl) and always exits 0.

Usage (preferred — never call pytest directly):
    python -m polygraph.pg_test [pytest-args...]

Examples:
    python -m polygraph.pg_test                       # full suite
    python -m polygraph.pg_test polygraph/tests/      # directory
    python -m polygraph.pg_test polygraph/tests/test_chain.py::test_tamper
"""

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import the chain helpers directly so pg_test shares the exact same
# hashing / append logic as record.py without duplication.
sys.path.insert(0, str(Path(__file__).parent.parent))
from hooks.record import _append_trace  # noqa: E402  (local import after sys.path)


_FULL_SUITE_MARKERS = re.compile(
    r"^(|--|-)v+$|^-[a-zA-Z]*x[a-zA-Z]*$"  # flag-only args
)


def _is_full_suite(args: list[str]) -> bool:
    """True when no positional path / node-id args were given."""
    positional = [
        a for a in args
        if not a.startswith("-") and not a.startswith("--")
    ]
    return len(positional) == 0


_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")
_ERROR_RE  = re.compile(r"(\d+) error")


def _parse_counts(output: str) -> tuple[int, int]:
    passed = int(m.group(1)) if (m := _PASSED_RE.search(output)) else 0
    failed = int(m.group(1)) if (m := _FAILED_RE.search(output)) else 0
    failed += int(m.group(1)) if (m := _ERROR_RE.search(output)) else 0
    return passed, failed


def run(args: list[str] | None = None) -> None:
    if args is None:
        args = sys.argv[1:]

    cmd = [sys.executable, "-m", "pytest"] + args
    ts = datetime.now(timezone.utc).isoformat()

    result = subprocess.run(cmd, capture_output=False)  # let output stream live

    combined = ""  # pytest already printed to the terminal; we re-run briefly
    # Re-capture just the summary line for count extraction
    summary_result = subprocess.run(
        cmd + ["--tb=no", "-q"],
        capture_output=True,
        text=True,
    )
    combined = summary_result.stdout + summary_result.stderr
    passed, failed = _parse_counts(combined)

    full_suite = _is_full_suite(args)
    command_str = " ".join(cmd)

    entry = {
        "ts": ts,
        "session_id": "",          # not invoked from a hook; no session context
        "tool_name": "pg_test",
        "category": "RUN_TEST",
        "target": command_str,
        "file_sha256": None,
        "full_suite": full_suite,
        "passed": passed,
        "failed": failed,
        "exit_code": result.returncode,
    }

    try:
        _append_trace(entry)
    except Exception as exc:  # noqa: BLE001
        print(f"pg_test: chain append failed: {exc}", file=sys.stderr)

    # Always exit 0
    sys.exit(0)


if __name__ == "__main__":
    run()
