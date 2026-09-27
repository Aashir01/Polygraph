"""
polygraph/commands/run_cmd.py
=============================
Implements ``python -m polygraph run start|end|list``.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
_PRIVATE_DIR = Path.home() / ".polygraph_private"
_GATE_OFF = _PRIVATE_DIR / "GATE_OFF"
_RESULTS_CSV = _ROOT / "experiment" / "results.csv"

_CSV_FIELDS = [
    "run_id", "ticket", "gate", "claimed_success", "first_verdict",
    "final_verdict", "blocked_count", "committed", "fixed_after_block",
    "duration_seconds",
]


def _git(*args: str, cwd: Path = _ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _current_commit() -> str:
    r = _git("rev-parse", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else ""


def _trace_line_count() -> int:
    trace = _PRIVATE_DIR / "trace.jsonl"
    if not trace.exists():
        return 0
    count = 0
    with open(trace, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _reset_demo_repo() -> bool:
    """Reset demo_repo/ to baseline tag.  Returns True if anything changed."""
    # Restore tracked files
    _git("restore", "--source=baseline", "--staged", "--worktree", "demo_repo/")
    # Remove untracked files
    subprocess.run(
        ["git", "clean", "-fd", "demo_repo/"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    # Check if there are now staged changes to commit
    r = _git("status", "--porcelain", "demo_repo/")
    return bool(r.stdout.strip())


def cmd_run(args: argparse.Namespace) -> None:
    """Dispatch run sub-commands."""
    if args.run_action == "start":
        _run_start(args.ticket, args.gate)
    elif args.run_action == "end":
        _run_end()
    elif args.run_action == "list":
        _run_list()
    else:
        print("Unknown run action.", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# run start
# ---------------------------------------------------------------------------

def _run_start(ticket: str, gate: str) -> None:
    """Reset demo_repo, set gate mode, record active_run.json."""
    from polygraph.run_recorder import (
        clear_active_run,
        load_active_run,
        save_active_run,
        _make_run_id,
    )

    # Warn if a run is already active
    existing = load_active_run()
    if existing:
        print(
            f"[warn] Existing run {existing.get('run_id')} is active — overwriting.",
            file=sys.stderr,
        )
        clear_active_run()

    print(f"Resetting demo_repo/ to baseline tag...")
    changed = _reset_demo_repo()

    # Commit the reset if anything changed
    start_commit = _current_commit()
    if changed:
        _git("add", "demo_repo/")
        run_id_tmp = f"t{ticket}_{gate}"
        r = _git("commit", "-m", f"reset for run {run_id_tmp}")
        if r.returncode == 0:
            start_commit = _current_commit()
            print(f"Committed reset: {start_commit[:8]}")
        else:
            print(f"[warn] reset commit failed: {r.stderr.strip()}", file=sys.stderr)
    else:
        print("demo_repo/ already at baseline — no commit needed.")

    # Set gate mode
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    if gate == "off":
        _GATE_OFF.touch()
        print("Gate: OFF")
    else:
        if _GATE_OFF.exists():
            _GATE_OFF.unlink()
        print("Gate: ON")

    run_id = _make_run_id(ticket, gate)
    start_ts = datetime.now(timezone.utc).isoformat()
    start_line = _trace_line_count()

    run_data = {
        "run_id": run_id,
        "ticket": ticket,
        "gate": gate,
        "start_ts": start_ts,
        "start_commit": start_commit,
        "start_trace_line": start_line,
        "block_count": 0,
    }
    save_active_run(run_data)
    print(f"Run started: {run_id}")
    print(f"  ticket={ticket}  gate={gate}  start_commit={start_commit[:8]}  trace_line={start_line}")


# ---------------------------------------------------------------------------
# run end
# ---------------------------------------------------------------------------

def _run_end() -> None:
    """Finalize the active run."""
    from polygraph.run_recorder import load_active_run, clear_active_run

    run = load_active_run()
    if run is None:
        print("No active run.", file=sys.stderr)
        sys.exit(1)

    # Run the verdict engine one last time to ensure results are up to date
    try:
        from polygraph.verdict import run_verdict
        result = run_verdict()
        from polygraph.run_recorder import record_verdict
        record_verdict(result)
        print(f"Final verdict: {result.get('verdict', 'UNKNOWN')}")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] verdict on end failed: {exc}", file=sys.stderr)

    run_id = run.get("run_id", "unknown")
    clear_active_run()
    print(f"Run {run_id} finalized.")


# ---------------------------------------------------------------------------
# run list
# ---------------------------------------------------------------------------

def _run_list() -> None:
    """Print results.csv as a plain table."""
    if not _RESULTS_CSV.exists():
        print("No results yet.  Run 'python -m polygraph run start ...' first.")
        return

    rows: list[dict] = []
    with open(_RESULTS_CSV, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(dict(row))

    if not rows:
        print("results.csv is empty.")
        return

    # Determine column widths
    headers = list(rows[0].keys())
    col_widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))

    sep = "  "
    header_line = sep.join(h.ljust(col_widths[h]) for h in headers)
    divider = sep.join("-" * col_widths[h] for h in headers)
    print(header_line)
    print(divider)
    for row in rows:
        print(sep.join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers))
