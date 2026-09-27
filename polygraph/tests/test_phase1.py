"""
polygraph/tests/test_phase1.py
==============================
Unit tests for PHASE 1 components:
  - gate_cmd (gate on/off/status)
  - run_recorder (active run CRUD, upsert)
  - gate.py GATE_BLOCK trace append
  - CLI __main__ invocation
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_verdict(verdict: str = "REJECTED") -> dict:
    return {
        "verdict": verdict,
        "ts": "2024-01-01T00:00:00+00:00",
        "checks": [
            {"name": "independent_test_run", "ok": False, "passed": 0, "failed": 1, "flags": []},
            {"name": "test_integrity", "ok": True, "flags": []},
            {"name": "trace_behavior", "ok": True, "test_after_edit": True, "full_suite_run": True, "flags": []},
            {"name": "claim_check", "ok": True, "claim_text": "", "sentences": [], "claim_source": "none"},
        ],
    }


# ---------------------------------------------------------------------------
# gate_cmd tests
# ---------------------------------------------------------------------------

class TestGateCmd:
    def test_gate_on_removes_gate_off(self, tmp_path):
        gate_off = tmp_path / "GATE_OFF"
        gate_off.touch()
        from polygraph.commands import gate_cmd
        with patch.object(gate_cmd, "_GATE_OFF", gate_off), \
             patch.object(gate_cmd, "_PRIVATE_DIR", tmp_path):
            gate_cmd.cmd_gate("on")
        assert not gate_off.exists()

    def test_gate_off_creates_gate_off(self, tmp_path):
        gate_off = tmp_path / "GATE_OFF"
        from polygraph.commands import gate_cmd
        with patch.object(gate_cmd, "_GATE_OFF", gate_off), \
             patch.object(gate_cmd, "_PRIVATE_DIR", tmp_path):
            gate_cmd.cmd_gate("off")
        assert gate_off.exists()

    def test_gate_status_on(self, tmp_path, capsys):
        gate_off = tmp_path / "GATE_OFF"
        from polygraph.commands import gate_cmd
        with patch.object(gate_cmd, "_GATE_OFF", gate_off), \
             patch.object(gate_cmd, "_PRIVATE_DIR", tmp_path):
            gate_cmd.cmd_gate("status")
        out = capsys.readouterr().out
        assert "ON" in out

    def test_gate_status_off(self, tmp_path, capsys):
        gate_off = tmp_path / "GATE_OFF"
        gate_off.touch()
        from polygraph.commands import gate_cmd
        with patch.object(gate_cmd, "_GATE_OFF", gate_off), \
             patch.object(gate_cmd, "_PRIVATE_DIR", tmp_path):
            gate_cmd.cmd_gate("status")
        out = capsys.readouterr().out
        assert "OFF" in out


# ---------------------------------------------------------------------------
# run_recorder tests
# ---------------------------------------------------------------------------

class TestRunRecorder:
    def _make_recorder(self, tmp_path: Path):
        """Return a recorder module with patched paths."""
        import polygraph.run_recorder as rr
        return rr

    def test_load_active_run_none_when_missing(self, tmp_path):
        import polygraph.run_recorder as rr
        with patch.object(rr, "_ACTIVE_RUN", tmp_path / "active_run.json"):
            result = rr.load_active_run()
        assert result is None

    def test_save_and_load_active_run(self, tmp_path):
        import polygraph.run_recorder as rr
        active_run_path = tmp_path / "active_run.json"
        with patch.object(rr, "_ACTIVE_RUN", active_run_path), \
             patch.object(rr, "_PRIVATE_DIR", tmp_path):
            rr.save_active_run({"run_id": "test_run", "ticket": "01"})
            loaded = rr.load_active_run()
        assert loaded["run_id"] == "test_run"

    def test_clear_active_run(self, tmp_path):
        import polygraph.run_recorder as rr
        active_run_path = tmp_path / "active_run.json"
        active_run_path.write_text('{"run_id": "x"}', encoding="utf-8")
        with patch.object(rr, "_ACTIVE_RUN", active_run_path):
            rr.clear_active_run()
        assert not active_run_path.exists()

    def test_upsert_inserts_new_row(self, tmp_path):
        import polygraph.run_recorder as rr
        csv_path = tmp_path / "results.csv"
        with patch.object(rr, "_RESULTS_CSV", csv_path):
            rr._upsert_result({"run_id": "r1", "ticket": "01", "gate": "on",
                               "claimed_success": "yes", "first_verdict": "REJECTED",
                               "final_verdict": "REJECTED", "blocked_count": 1,
                               "committed": "no", "fixed_after_block": "no",
                               "duration_seconds": 10.0})
        assert csv_path.exists()
        rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["run_id"] == "r1"

    def test_upsert_deduplicates(self, tmp_path):
        import polygraph.run_recorder as rr
        csv_path = tmp_path / "results.csv"
        row = {"run_id": "r1", "ticket": "01", "gate": "on",
               "claimed_success": "yes", "first_verdict": "REJECTED",
               "final_verdict": "REJECTED", "blocked_count": 1,
               "committed": "no", "fixed_after_block": "no",
               "duration_seconds": 10.0}
        with patch.object(rr, "_RESULTS_CSV", csv_path):
            rr._upsert_result(row)
            row["final_verdict"] = "VERIFIED"  # update
            rr._upsert_result(row)
        rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["final_verdict"] == "VERIFIED"

    def test_record_verdict_no_active_run(self, tmp_path):
        """record_verdict is a no-op when no run is active."""
        import polygraph.run_recorder as rr
        with patch.object(rr, "_ACTIVE_RUN", tmp_path / "active_run.json"):
            # Should not raise
            rr.record_verdict(_make_minimal_verdict())

    def test_record_verdict_writes_run_file(self, tmp_path):
        import polygraph.run_recorder as rr
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        csv_path = tmp_path / "results.csv"
        active_run_path = tmp_path / "active_run.json"

        from polygraph.run_recorder import _make_run_id
        run_id = _make_run_id("01", "on")

        run_data = {
            "run_id": run_id,
            "ticket": "01",
            "gate": "on",
            "start_ts": "2024-01-01T00:00:00+00:00",
            "start_commit": "",
            "start_trace_line": 0,
            "block_count": 0,
        }
        active_run_path.write_text(json.dumps(run_data), encoding="utf-8")

        with patch.object(rr, "_ACTIVE_RUN", active_run_path), \
             patch.object(rr, "_PRIVATE_DIR", tmp_path), \
             patch.object(rr, "_RUNS_DIR", runs_dir), \
             patch.object(rr, "_RESULTS_CSV", csv_path), \
             patch.object(rr, "_TRACE", tmp_path / "trace.jsonl"), \
             patch.object(rr, "_demo_repo_commit_made_after", return_value=False), \
             patch.object(rr, "_check_log_integrity", return_value="VALID"):
            rr.record_verdict(_make_minimal_verdict("REJECTED"))

        run_file = runs_dir / f"{run_id}.json"
        assert run_file.exists()
        doc = json.loads(run_file.read_text(encoding="utf-8"))
        assert doc["verdict"] == "REJECTED"
        assert doc["run_id"] == run_id

    def test_record_verdict_upserts_csv(self, tmp_path):
        import polygraph.run_recorder as rr
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        csv_path = tmp_path / "results.csv"
        active_run_path = tmp_path / "active_run.json"

        from polygraph.run_recorder import _make_run_id
        run_id = _make_run_id("02", "off")

        run_data = {
            "run_id": run_id,
            "ticket": "02",
            "gate": "off",
            "start_ts": "2024-01-01T00:00:00+00:00",
            "start_commit": "",
            "start_trace_line": 0,
            "block_count": 0,
        }
        active_run_path.write_text(json.dumps(run_data), encoding="utf-8")

        with patch.object(rr, "_ACTIVE_RUN", active_run_path), \
             patch.object(rr, "_PRIVATE_DIR", tmp_path), \
             patch.object(rr, "_RUNS_DIR", runs_dir), \
             patch.object(rr, "_RESULTS_CSV", csv_path), \
             patch.object(rr, "_TRACE", tmp_path / "trace.jsonl"), \
             patch.object(rr, "_demo_repo_commit_made_after", return_value=False), \
             patch.object(rr, "_check_log_integrity", return_value="VALID"):
            rr.record_verdict(_make_minimal_verdict("REJECTED"))

        rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["run_id"] == run_id
        assert rows[0]["ticket"] == "02"
        assert rows[0]["gate"] == "off"


# ---------------------------------------------------------------------------
# GATE_BLOCK trace entry tests
# ---------------------------------------------------------------------------

class TestGateBlockTrace:
    def test_append_gate_block_writes_valid_entry(self, tmp_path):
        """_append_gate_block writes a hash-chained GATE_BLOCK entry."""
        import importlib
        import hooks.gate as gate_module
        importlib.reload(gate_module)

        trace_path = tmp_path / "trace.jsonl"
        private_dir = tmp_path

        with patch.object(gate_module, "_TRACE", trace_path), \
             patch.object(gate_module, "_PRIVATE_DIR", private_dir):
            gate_module._append_gate_block("git commit -m test", "REJECTED", "sess1")

        assert trace_path.exists()
        lines = [l.strip() for l in trace_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["category"] == "GATE_BLOCK"
        assert entry["blocked_verdict"] == "REJECTED"
        assert "hash" in entry
        assert "prev_hash" in entry
        # Verify hash correctness
        entry_for_hash = {k: v for k, v in entry.items() if k != "hash"}
        entry_json = json.dumps(entry_for_hash, ensure_ascii=False, sort_keys=True)
        expected = hashlib.sha256((entry["prev_hash"] + entry_json).encode()).hexdigest()
        assert entry["hash"] == expected

    def test_gate_block_chain_links_correctly(self, tmp_path):
        """Two GATE_BLOCK entries chain prev_hash correctly."""
        import importlib
        import hooks.gate as gate_module
        importlib.reload(gate_module)

        trace_path = tmp_path / "trace.jsonl"

        with patch.object(gate_module, "_TRACE", trace_path), \
             patch.object(gate_module, "_PRIVATE_DIR", tmp_path):
            gate_module._append_gate_block("git commit -m a", "REJECTED", "s1")
            gate_module._append_gate_block("git push", "NEEDS_REVIEW", "s1")

        lines = [l.strip() for l in trace_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])
        assert e2["prev_hash"] == e1["hash"]


# ---------------------------------------------------------------------------
# run list
# ---------------------------------------------------------------------------

class TestRunList:
    def test_run_list_with_data(self, tmp_path, capsys):
        import polygraph.commands.run_cmd as rc
        csv_path = tmp_path / "results.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "run_id", "ticket", "gate", "claimed_success", "first_verdict",
                "final_verdict", "blocked_count", "committed", "fixed_after_block",
                "duration_seconds"
            ])
            writer.writeheader()
            writer.writerow({
                "run_id": "t01_on_20240101", "ticket": "01", "gate": "on",
                "claimed_success": "yes", "first_verdict": "VERIFIED",
                "final_verdict": "VERIFIED", "blocked_count": 0,
                "committed": "yes", "fixed_after_block": "n/a",
                "duration_seconds": 120.0,
            })

        with patch.object(rc, "_RESULTS_CSV", csv_path):
            rc._run_list()

        out = capsys.readouterr().out
        assert "t01_on_20240101" in out
        assert "VERIFIED" in out
