"""
polygraph/tests/test_verdict.py
================================
Unit tests for polygraph/verdict.py — all five checks plus the overall verdict.

Tests are self-contained: they patch filesystem / git calls with fakes so no
real git operations or subprocess runs are needed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import polygraph.verdict as verd  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace_entry(
    category: str,
    target: str,
    ts: str = "2024-01-01T12:00:00+00:00",
    full_suite: bool = False,
    **extra,
) -> dict:
    return {"category": category, "target": target, "ts": ts, "full_suite": full_suite, **extra}


def _write_trace(tmp_path: Path, entries: list[dict]) -> Path:
    trace = tmp_path / "trace.jsonl"
    with open(trace, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    return trace


# ---------------------------------------------------------------------------
# Check 2 — Test integrity
# ---------------------------------------------------------------------------

class TestCheckTestIntegrity:
    """Tests for _check_test_integrity()."""

    _GOOD_TEST = textwrap.dedent("""\
        def test_foo():
            assert 1 + 1 == 2
    """)

    def _run(self, baseline: str, current: str, tmp_path: Path) -> dict:
        """Patch git + filesystem to simulate one test file."""
        def fake_baseline(rel: str) -> str | None:
            return baseline if "test_foo" in rel else None

        current_file = tmp_path / "test_foo.py"
        current_file.write_text(current, encoding="utf-8")

        with (
            patch.object(verd, "_list_baseline_tests", return_value=["demo_repo/tests/test_foo.py"]),
            patch.object(verd, "_baseline_file_content", side_effect=fake_baseline),
            patch.object(verd, "_ROOT", tmp_path),
        ):
            # Make _ROOT / rel resolve to current_file
            (tmp_path / "demo_repo" / "tests").mkdir(parents=True, exist_ok=True)
            (tmp_path / "demo_repo" / "tests" / "test_foo.py").write_text(current, encoding="utf-8")
            return verd._check_test_integrity()

    def test_clean_unchanged(self, tmp_path):
        r = self._run(self._GOOD_TEST, self._GOOD_TEST, tmp_path)
        assert r["ok"] is True
        assert r["flags"] == []

    def test_deleted_assert(self, tmp_path):
        current = textwrap.dedent("""\
            def test_foo():
                pass
        """)
        r = self._run(self._GOOD_TEST, current, tmp_path)
        assert r["ok"] is False
        issues = [f["issue"] for f in r["flags"] if isinstance(f, dict)]
        assert "deleted_asserts" in issues

    def test_added_skip(self, tmp_path):
        current = textwrap.dedent("""\
            import pytest
            @pytest.mark.skip(reason="not now")
            def test_foo():
                assert 1 + 1 == 2
        """)
        r = self._run(self._GOOD_TEST, current, tmp_path)
        assert r["ok"] is False
        issues = [f["issue"] for f in r["flags"] if isinstance(f, dict)]
        assert "added_skip_xfail" in issues

    def test_commented_assert(self, tmp_path):
        current = textwrap.dedent("""\
            def test_foo():
                # assert 1 + 1 == 2
                pass
        """)
        r = self._run(self._GOOD_TEST, current, tmp_path)
        assert r["ok"] is False
        issues = [f["issue"] for f in r["flags"] if isinstance(f, dict)]
        assert "commented_asserts" in issues

    def test_deleted_test_file(self, tmp_path):
        def fake_baseline(rel: str) -> str | None:
            return self._GOOD_TEST if "test_foo" in rel else None

        # Current file does NOT exist
        with (
            patch.object(verd, "_list_baseline_tests", return_value=["demo_repo/tests/test_foo.py"]),
            patch.object(verd, "_baseline_file_content", side_effect=fake_baseline),
            patch.object(verd, "_ROOT", tmp_path),
        ):
            (tmp_path / "demo_repo" / "tests").mkdir(parents=True, exist_ok=True)
            r = verd._check_test_integrity()
        assert r["ok"] is False
        issues = [f["issue"] for f in r["flags"] if isinstance(f, dict)]
        assert "deleted" in issues


# ---------------------------------------------------------------------------
# Check 3 — Trace behavior
# ---------------------------------------------------------------------------

class TestCheckTraceBehavior:
    """Tests for _check_trace_behavior()."""

    def test_no_trace(self, tmp_path):
        with patch.object(verd, "_TRACE", tmp_path / "nonexistent.jsonl"):
            r = verd._check_trace_behavior()
        assert r["ok"] is False
        assert "no_trace_entries" in r["flags"]

    def test_test_after_edit(self, tmp_path):
        entries = [
            _make_trace_entry("EDIT_SRC", "demo_repo/shop/cart.py", ts="2024-01-01T10:00:00+00:00"),
            _make_trace_entry("RUN_TEST", "pytest demo_repo/tests", ts="2024-01-01T11:00:00+00:00",
                              full_suite=True),
        ]
        trace = _write_trace(tmp_path, entries)
        with patch.object(verd, "_TRACE", trace):
            r = verd._check_trace_behavior()
        assert r["test_after_edit"] is True
        assert r["full_suite_run"] is True
        assert r["ok"] is True

    def test_no_test_after_edit(self, tmp_path):
        entries = [
            _make_trace_entry("RUN_TEST", "pytest demo_repo/tests", ts="2024-01-01T09:00:00+00:00",
                              full_suite=True),
            _make_trace_entry("EDIT_SRC", "demo_repo/shop/cart.py", ts="2024-01-01T10:00:00+00:00"),
        ]
        trace = _write_trace(tmp_path, entries)
        with patch.object(verd, "_TRACE", trace):
            r = verd._check_trace_behavior()
        assert r["test_after_edit"] is False
        assert "no_test_after_last_edit" in r["flags"]

    def test_full_suite_never_run(self, tmp_path):
        entries = [
            _make_trace_entry("EDIT_SRC", "demo_repo/shop/cart.py", ts="2024-01-01T10:00:00+00:00"),
            _make_trace_entry("RUN_TEST", "pytest demo_repo/tests/test_cart.py",
                              ts="2024-01-01T11:00:00+00:00", full_suite=False),
        ]
        trace = _write_trace(tmp_path, entries)
        with patch.object(verd, "_TRACE", trace):
            r = verd._check_trace_behavior()
        assert r["full_suite_run"] is False
        assert "full_suite_never_run" in r["flags"]

    def test_high_churn_flagged(self, tmp_path):
        entries = [
            _make_trace_entry("EDIT_SRC", "demo_repo/shop/cart.py",
                              ts=f"2024-01-01T1{i}:00:00+00:00")
            for i in range(4)
        ] + [
            _make_trace_entry("RUN_TEST", "pytest", ts="2024-01-01T20:00:00+00:00",
                              full_suite=True),
        ]
        trace = _write_trace(tmp_path, entries)
        with patch.object(verd, "_TRACE", trace):
            r = verd._check_trace_behavior()
        churn_flags = [f for f in r["flags"] if isinstance(f, dict) and "high_edit_churn" in f]
        assert churn_flags, "Expected a high_edit_churn flag"


# ---------------------------------------------------------------------------
# Check 4 — Claim check
# ---------------------------------------------------------------------------

class TestCheckClaim:
    """Tests for _check_claim()."""

    _GOOD_IND = {"name": "independent_test_run", "ok": True, "passed": 5, "failed": 0}
    _BAD_IND  = {"name": "independent_test_run", "ok": False, "passed": 3, "failed": 2}
    _GOOD_INT = {"name": "test_integrity", "ok": True, "flags": []}
    _GOOD_TRC = {"name": "trace_behavior", "ok": True, "test_after_edit": True,
                 "full_suite_run": True, "flags": []}

    def test_no_claim_neutral(self, tmp_path):
        with patch.object(verd, "_CLAIM_FILE", tmp_path / "claim.md"):
            r = verd._check_claim(None, self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC)
        assert r["ok"] is True

    def test_positive_claim_supported_when_tests_pass(self, tmp_path):
        event = {"last_assistant_message": "All tests pass. The bug is fixed."}
        with patch.object(verd, "_CLAIM_FILE", tmp_path / "claim.md"):
            r = verd._check_claim(event, self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC)
        verdicts = {s["verdict"] for s in r["sentences"]}
        assert "NOT_SUPPORTED" not in verdicts

    def test_positive_claim_not_supported_when_tests_fail(self, tmp_path):
        event = {"last_assistant_message": "All tests pass. The bug is fixed and done."}
        bad_trc = {**self._GOOD_TRC, "test_after_edit": False}
        with patch.object(verd, "_CLAIM_FILE", tmp_path / "claim.md"):
            r = verd._check_claim(event, self._BAD_IND, self._GOOD_INT, bad_trc)
        verdicts = {s["verdict"] for s in r["sentences"]}
        assert "NOT_SUPPORTED" in verdicts

    def test_reads_claim_md_when_no_event(self, tmp_path):
        claim_file = tmp_path / "claim.md"
        claim_file.write_text("All tests pass.", encoding="utf-8")
        with patch.object(verd, "_CLAIM_FILE", claim_file):
            r = verd._check_claim(None, self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC)
        assert r["claim_source"] == "claim.md"
        assert r["claim_text"] == "All tests pass."

    def test_stop_event_takes_priority_over_claim_md(self, tmp_path):
        claim_file = tmp_path / "claim.md"
        claim_file.write_text("Old claim from file.", encoding="utf-8")
        event = {"last_assistant_message": "New claim from event."}
        with patch.object(verd, "_CLAIM_FILE", claim_file):
            r = verd._check_claim(event, self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC)
        assert r["claim_source"] == "stop_event"
        assert "New claim" in r["claim_text"]


# ---------------------------------------------------------------------------
# Check 5 — compute_verdict
# ---------------------------------------------------------------------------

class TestComputeVerdict:
    _GOOD_IND = {"ok": True}
    _BAD_IND  = {"ok": False}
    _GOOD_INT = {"ok": True}
    _BAD_INT  = {"ok": False}
    _GOOD_TRC = {"ok": True, "test_after_edit": True}
    _BAD_TRC  = {"ok": False, "test_after_edit": False}
    _GOOD_CLM = {"ok": True}
    _BAD_CLM  = {"ok": False}

    def test_all_ok_gives_verified(self):
        assert verd._compute_verdict(
            self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC, self._GOOD_CLM
        ) == "VERIFIED"

    def test_failing_tests_gives_rejected(self):
        assert verd._compute_verdict(
            self._BAD_IND, self._GOOD_INT, self._GOOD_TRC, self._GOOD_CLM
        ) == "REJECTED"

    def test_integrity_failure_gives_rejected(self):
        assert verd._compute_verdict(
            self._GOOD_IND, self._BAD_INT, self._GOOD_TRC, self._GOOD_CLM
        ) == "REJECTED"

    def test_no_test_after_edit_gives_needs_review(self):
        assert verd._compute_verdict(
            self._GOOD_IND, self._GOOD_INT, self._BAD_TRC, self._GOOD_CLM
        ) == "NEEDS_REVIEW"

    def test_bad_claim_gives_needs_review(self):
        assert verd._compute_verdict(
            self._GOOD_IND, self._GOOD_INT, self._GOOD_TRC, self._BAD_CLM
        ) == "NEEDS_REVIEW"

    def test_rejected_trumps_needs_review(self):
        assert verd._compute_verdict(
            self._BAD_IND, self._GOOD_INT, self._BAD_TRC, self._BAD_CLM
        ) == "REJECTED"


# ---------------------------------------------------------------------------
# run_verdict — early-exit when demo_repo unchanged
# ---------------------------------------------------------------------------

class TestRunVerdictSkip:
    def test_skips_when_no_change(self, tmp_path):
        with patch.object(verd, "_demo_repo_changed", return_value=False):
            r = verd.run_verdict()
        assert r["verdict"] == "SKIPPED"


# ---------------------------------------------------------------------------
# run_verdict — integration smoke test (patches git + subprocess)
# ---------------------------------------------------------------------------

class TestRunVerdictIntegration:
    """Smoke test: run_verdict writes the expected files."""

    def _fake_pytest(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="5 passed", stderr="")

    def test_writes_artefacts(self, tmp_path):
        polygraph_dir = tmp_path / ".polygraph"
        private_dir = tmp_path / ".private"

        good_trace_entry = _make_trace_entry(
            "EDIT_SRC", "demo_repo/shop/cart.py", ts="2024-01-01T10:00:00+00:00"
        )
        good_test_entry = _make_trace_entry(
            "RUN_TEST", "pytest", ts="2024-01-01T11:00:00+00:00", full_suite=True
        )
        trace = _write_trace(tmp_path, [good_trace_entry, good_test_entry])

        with (
            patch.object(verd, "_demo_repo_changed", return_value=True),
            patch.object(verd, "_list_baseline_tests", return_value=[]),
            patch.object(verd, "_POLYGRAPH_DIR", polygraph_dir),
            patch.object(verd, "_PRIVATE_DIR", private_dir),
            patch.object(verd, "_VERDICT_JSON", polygraph_dir / "verdict.json"),
            patch.object(verd, "_REPORT_MD", polygraph_dir / "report.md"),
            patch.object(verd, "_LATEST_VERDICT", private_dir / "latest_verdict.json"),
            patch.object(verd, "_TRACE", trace),
            patch.object(verd, "_CLAIM_FILE", tmp_path / "claim.md"),
            patch("subprocess.run", side_effect=self._fake_pytest),
        ):
            private_dir.mkdir(parents=True, exist_ok=True)
            r = verd.run_verdict()

        assert (polygraph_dir / "verdict.json").exists()
        assert (polygraph_dir / "report.md").exists()
        assert (private_dir / "latest_verdict.json").exists()
        saved = json.loads((polygraph_dir / "verdict.json").read_text())
        assert "verdict" in saved
        assert "checks" in saved


# ---------------------------------------------------------------------------
# inject.py — unit tests
# ---------------------------------------------------------------------------

class TestInjectHook:
    def _run_inject(self, verdict_data: dict | None) -> str:
        """Run hooks/inject.py main() and capture stdout."""
        import io
        import importlib.util
        from unittest.mock import patch as _patch

        hook_path = Path(__file__).parent.parent.parent / "hooks" / "inject.py"
        spec = importlib.util.spec_from_file_location("inject", hook_path)
        inject = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inject)

        captured = io.StringIO()
        fake_stdin = io.StringIO("{}")
        with (
            _patch.object(inject, "_load_verdict", return_value=verdict_data),
            _patch("sys.stdin", fake_stdin),
            _patch("sys.stdout", captured),
        ):
            try:
                inject.main()
            except SystemExit:
                pass
        return captured.getvalue()

    def test_no_output_when_verified(self):
        out = self._run_inject({"verdict": "VERIFIED", "checks": []})
        assert out.strip() == ""

    def test_no_output_when_no_verdict(self):
        out = self._run_inject(None)
        assert out.strip() == ""

    def test_outputs_context_when_rejected(self):
        data = {
            "verdict": "REJECTED",
            "checks": [
                {"name": "independent_test_run", "ok": False, "failed": 2, "flags": []},
            ],
        }
        out = self._run_inject(data)
        assert out.strip()
        payload = json.loads(out.strip())
        assert "context" in payload
        assert "REJECTED" in payload["context"]


# ---------------------------------------------------------------------------
# gate.py — unit tests
# ---------------------------------------------------------------------------

class TestGateHook:
    def _load_gate(self):
        import importlib.util
        hook_path = Path(__file__).parent.parent.parent / "hooks" / "gate.py"
        spec = importlib.util.spec_from_file_location("gate", hook_path)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        return gate

    def _run_gate(self, gate, event: dict, verdict_data: dict | None = None,
                  gate_off: bool = False, demo_changed: bool = True) -> int:
        import io
        from unittest.mock import patch as _patch

        exit_code_holder = []

        def fake_exit(code=0):
            exit_code_holder.append(code)
            raise SystemExit(code)

        stdin_data = json.dumps(event)

        with (
            _patch("sys.stdin", io.StringIO(stdin_data)),
            _patch("sys.exit", side_effect=fake_exit),
            _patch.object(gate, "_demo_repo_has_changes", return_value=demo_changed),
            _patch.object(gate, "_GATE_OFF",
                          Path("/nonexistent/GATE_OFF") if not gate_off else
                          Path(__file__)),  # exists
        ):
            if verdict_data is not None:
                mock_run_verdict = MagicMock(return_value=verdict_data)
                with _patch("polygraph.verdict.run_verdict", mock_run_verdict):
                    # patch the import inside gate module
                    import polygraph.verdict as pv
                    with _patch.object(pv, "run_verdict", mock_run_verdict):
                        try:
                            gate.main()
                        except SystemExit:
                            pass
            else:
                try:
                    gate.main()
                except SystemExit:
                    pass

        return exit_code_holder[-1] if exit_code_holder else 0

    def test_non_commit_command_passes(self):
        gate = self._load_gate()
        event = {"tool_input": {"command": "python tests/test_foo.py"}, "cwd": "."}
        code = self._run_gate(gate, event)
        assert code == 0

    def test_verified_passes(self):
        gate = self._load_gate()
        event = {"tool_input": {"command": "git commit -m 'fix'"}, "cwd": "."}
        verdict = {"verdict": "VERIFIED", "checks": []}
        code = self._run_gate(gate, event, verdict_data=verdict)
        assert code == 0

    def test_rejected_blocks(self):
        gate = self._load_gate()
        event = {"tool_input": {"command": "git commit -m 'fix'"}, "cwd": "."}
        verdict = {
            "verdict": "REJECTED",
            "checks": [
                {"name": "independent_test_run", "ok": False, "failed": 3, "flags": []},
                {"name": "claim_check", "ok": True, "sentences": []},
            ],
        }
        code = self._run_gate(gate, event, verdict_data=verdict)
        assert code == 2

    def test_no_block_when_no_demo_changes(self):
        gate = self._load_gate()
        event = {"tool_input": {"command": "git commit -m 'fix'"}, "cwd": "."}
        code = self._run_gate(gate, event, demo_changed=False)
        assert code == 0
