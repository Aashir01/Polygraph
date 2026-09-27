"""
polygraph/run_recorder.py
=========================
Manages active experiment runs and persists their results.

An "active run" is described by ~/.polygraph_private/active_run.json which is
written by ``run start`` and cleared by ``run end``.

Whenever a verdict is computed (Stop hook or gate) and a run is active, this
module writes:
  - dashboard/data/runs/<run_id>.json  (full structured evidence)
  - experiment/results.csv             (one upserted summary row)

Public API
----------
load_active_run()   -> dict | None
save_active_run(d)  -> None
clear_active_run()  -> None
record_verdict(verdict_result, gate_block=False) -> None
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent
_PRIVATE_DIR = Path.home() / ".polygraph_private"
_ACTIVE_RUN = _PRIVATE_DIR / "active_run.json"
_TRACE = _PRIVATE_DIR / "trace.jsonl"

_RUNS_DIR = _ROOT / "dashboard" / "data" / "runs"
_RESULTS_CSV = _ROOT / "experiment" / "results.csv"

_CSV_FIELDS = [
    "run_id", "ticket", "gate", "claimed_success", "first_verdict",
    "final_verdict", "blocked_count", "committed", "fixed_after_block",
    "duration_seconds",
]


# ---------------------------------------------------------------------------
# Active run helpers
# ---------------------------------------------------------------------------

def load_active_run() -> dict | None:
    """Return the active run dict, or None if no run is active."""
    if not _ACTIVE_RUN.exists():
        return None
    try:
        return json.loads(_ACTIVE_RUN.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def save_active_run(data: dict) -> None:
    """Persist the active run dict."""
    _PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    _ACTIVE_RUN.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_active_run() -> None:
    """Remove active_run.json (run ended)."""
    if _ACTIVE_RUN.exists():
        _ACTIVE_RUN.unlink()


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------

def _count_trace_lines() -> int:
    """Return the current number of non-empty lines in trace.jsonl."""
    if not _TRACE.exists():
        return 0
    count = 0
    with open(_TRACE, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _read_trace_from(start_line: int) -> list[dict]:
    """Return trace entries from *start_line* (0-based) onwards."""
    entries: list[dict] = []
    if not _TRACE.exists():
        return entries
    with open(_TRACE, "r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            if idx >= start_line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

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


def _demo_repo_commit_made_after(start_commit: str) -> bool:
    """True if any commit touching demo_repo/ was made after start_commit."""
    if not start_commit:
        return False
    r = _git("log", f"{start_commit}..HEAD", "--oneline", "--", "demo_repo/")
    return bool(r.stdout.strip())


# ---------------------------------------------------------------------------
# Log integrity
# ---------------------------------------------------------------------------

def _check_log_integrity() -> str:
    """Return 'VALID' or 'TAMPERED' from verify_chain."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "polygraph.verify_chain"],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (r.stdout + r.stderr).strip()
        return "VALID" if "VALID" in out and "TAMPERED" not in out else "TAMPERED"
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# Run ID generation
# ---------------------------------------------------------------------------

def _make_run_id(ticket: str, gate: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"t{ticket}_{gate}_{ts}"


# ---------------------------------------------------------------------------
# Results CSV helpers
# ---------------------------------------------------------------------------

def _load_results() -> list[dict]:
    if not _RESULTS_CSV.exists():
        return []
    rows: list[dict] = []
    with open(_RESULTS_CSV, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(dict(row))
    return rows


def _save_results(rows: list[dict]) -> None:
    _RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(_RESULTS_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _upsert_result(row: dict) -> None:
    """Insert or update the results.csv row for row['run_id']."""
    rows = _load_results()
    updated = False
    for i, r in enumerate(rows):
        if r.get("run_id") == row["run_id"]:
            rows[i] = row
            updated = True
            break
    if not updated:
        rows.append(row)
    _save_results(rows)


# ---------------------------------------------------------------------------
# Public: record_verdict
# ---------------------------------------------------------------------------

def record_verdict(
    verdict_result: dict,
    gate_block: bool = False,
) -> None:
    """
    Called by the Stop hook and the gate whenever a verdict is computed.

    If no run is active, does nothing.
    Otherwise updates dashboard/data/runs/<run_id>.json and experiment/results.csv.

    Parameters
    ----------
    verdict_result : dict
        The dict returned by run_verdict().
    gate_block : bool
        True when called from the gate on a block event (not a stop).
    """
    run = load_active_run()
    if run is None:
        return

    run_id: str = run.get("run_id", "unknown")
    ticket: str = run.get("ticket", "")
    gate: str = run.get("gate", "on")
    start_commit: str = run.get("start_commit", "")
    start_line: int = run.get("start_trace_line", 0)
    start_ts: str = run.get("start_ts", "")

    verdict: str = verdict_result.get("verdict", "UNKNOWN")
    checks: list[dict] = verdict_result.get("checks", [])

    # Extract claim info
    claim_check: dict[str, Any] = next(
        (c for c in checks if c.get("name") == "claim_check"), {}
    )
    claim_text: str = claim_check.get("claim_text", "")
    claim_sentences: list[dict] = claim_check.get("sentences", [])
    claimed_success: bool = any(
        s.get("verdict") == "SUPPORTED"
        for s in claim_sentences
    ) or bool(claim_text.strip())

    # Extract test integrity findings
    integrity_check: dict = next(
        (c for c in checks if c.get("name") == "test_integrity"), {}
    )
    test_integrity_flags: list = integrity_check.get("flags", [])

    # Original test result
    ind_check: dict = next(
        (c for c in checks if c.get("name") == "independent_test_run"), {}
    )

    # Trace slice for this run
    trace_events = _read_trace_from(start_line)

    # Count GATE_BLOCK events in trace
    gate_blocks_in_trace = sum(
        1 for e in trace_events if e.get("category") == "GATE_BLOCK"
    )
    if gate_block:
        gate_blocks_in_trace += 1  # current block hasn't been written yet

    # Did a commit touching demo_repo happen after start?
    committed = _demo_repo_commit_made_after(start_commit)

    # Log integrity
    log_integrity = _check_log_integrity()

    # Duration
    duration_seconds: float = 0.0
    if start_ts:
        try:
            start_dt = datetime.fromisoformat(start_ts)
            now = datetime.now(timezone.utc)
            duration_seconds = (now - start_dt).total_seconds()
        except ValueError:
            pass

    # First vs final verdict — read existing run file if any
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_file = _RUNS_DIR / f"{run_id}.json"

    first_verdict: str = verdict
    if run_file.exists():
        try:
            existing = json.loads(run_file.read_text(encoding="utf-8"))
            first_verdict = existing.get("first_verdict", verdict)
        except Exception:  # noqa: BLE001
            pass

    run_doc: dict[str, Any] = {
        "run_id": run_id,
        "ticket": ticket,
        "gate": gate,
        "verdict": verdict,
        "first_verdict": first_verdict,
        "final_verdict": verdict,
        "claim_text": claim_text,
        "claim_sentences": claim_sentences,
        "evidence_checks": checks,
        "test_integrity_flags": test_integrity_flags,
        "original_tests": ind_check,
        "log_integrity": log_integrity,
        "trace_events": trace_events,
        "gate_block_count": gate_blocks_in_trace,
        "claimed_success": claimed_success,
        "committed": committed,
        "duration_seconds": round(duration_seconds, 1),
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    run_file.write_text(json.dumps(run_doc, indent=2), encoding="utf-8")

    # Upsert results.csv
    fixed_after_block = (
        "yes" if (gate_blocks_in_trace > 0 and verdict == "VERIFIED") else
        ("n/a" if gate_blocks_in_trace == 0 else "no")
    )

    csv_row: dict[str, Any] = {
        "run_id": run_id,
        "ticket": ticket,
        "gate": gate,
        "claimed_success": "yes" if claimed_success else "no",
        "first_verdict": first_verdict,
        "final_verdict": verdict,
        "blocked_count": gate_blocks_in_trace,
        "committed": "yes" if committed else "no",
        "fixed_after_block": fixed_after_block,
        "duration_seconds": round(duration_seconds, 1),
    }
    _upsert_result(csv_row)

    # Update active_run with latest block count
    run["block_count"] = gate_blocks_in_trace
    save_active_run(run)
