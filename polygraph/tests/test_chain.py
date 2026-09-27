"""
polygraph/tests/test_chain.py
Unit tests for the hash-chain integrity verifier.
"""

import hashlib
import json
import sys
from io import StringIO
from pathlib import Path

import pytest

# Ensure the project root is importable regardless of how pytest is invoked
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from polygraph.verify_chain import verify  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENESIS = "0" * 64


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _make_entry(prev_hash: str, **kwargs) -> dict:
    """Build a valid chain entry, computing the correct hash."""
    entry = {"prev_hash": prev_hash, "ts": "2024-01-01T00:00:00+00:00", **kwargs}
    entry_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    entry["hash"] = _sha256(prev_hash + entry_json)
    return entry


def _write_chain(tmp_path: Path, entries: list[dict]) -> Path:
    trace = tmp_path / "trace.jsonl"
    with open(trace, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    return trace


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_empty_chain(tmp_path, capsys):
    """An empty (non-existent) file is VALID."""
    result = verify(tmp_path / "nonexistent.jsonl")
    assert result is True
    assert "VALID" in capsys.readouterr().out


def test_single_valid_entry(tmp_path, capsys):
    """A single correctly hashed entry is VALID."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    trace = _write_chain(tmp_path, [e1])
    assert verify(trace) is True
    assert "VALID" in capsys.readouterr().out


def test_multi_entry_valid_chain(tmp_path, capsys):
    """Multiple correctly chained entries are VALID."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    e2 = _make_entry(e1["hash"], tool_name="execute_command", category="RUN_TEST")
    e3 = _make_entry(e2["hash"], tool_name="read_file", category="READ")
    trace = _write_chain(tmp_path, [e1, e2, e3])
    assert verify(trace) is True
    assert "VALID" in capsys.readouterr().out


def test_tampered_middle_line(tmp_path, capsys):
    """Editing a middle line's payload makes verify_chain report TAMPERED."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    e2 = _make_entry(e1["hash"], tool_name="execute_command", category="RUN_TEST")
    e3 = _make_entry(e2["hash"], tool_name="read_file", category="READ")
    trace = _write_chain(tmp_path, [e1, e2, e3])

    # Tamper: change e2's category in the file (hash stays the same → mismatch)
    lines = trace.read_text(encoding="utf-8").splitlines()
    tampered_entry = json.loads(lines[1])
    tampered_entry["category"] = "EDIT_SRC"  # was RUN_TEST
    lines[1] = json.dumps(tampered_entry, ensure_ascii=False, sort_keys=True)
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify(trace)
    out = capsys.readouterr().out
    assert result is False
    assert "TAMPERED" in out


def test_tampered_first_line(tmp_path, capsys):
    """Editing the first entry's payload makes verify_chain report TAMPERED."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    e2 = _make_entry(e1["hash"], tool_name="read_file", category="READ")
    trace = _write_chain(tmp_path, [e1, e2])

    lines = trace.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[0])
    bad["tool_name"] = "inject"
    lines[0] = json.dumps(bad, ensure_ascii=False, sort_keys=True)
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify(trace)
    assert result is False
    assert "TAMPERED" in capsys.readouterr().out


def test_tampered_hash_only(tmp_path, capsys):
    """Changing only the stored hash (not the payload) is also detected."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    trace = _write_chain(tmp_path, [e1])

    lines = trace.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[0])
    bad["hash"] = "a" * 64   # plausible-looking but wrong
    lines[0] = json.dumps(bad, ensure_ascii=False, sort_keys=True)
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify(trace)
    assert result is False
    assert "TAMPERED" in capsys.readouterr().out


def test_broken_prev_hash_link(tmp_path, capsys):
    """Breaking the prev_hash link between entries is detected."""
    e1 = _make_entry(_GENESIS, tool_name="write_file", category="EDIT_SRC")
    e2 = _make_entry(e1["hash"], tool_name="read_file", category="READ")
    trace = _write_chain(tmp_path, [e1, e2])

    lines = trace.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[1])
    bad["prev_hash"] = "b" * 64   # doesn't match e1["hash"]
    # Recompute hash so the per-entry check passes, but chain link breaks
    entry_for_hash = {k: v for k, v in bad.items() if k != "hash"}
    entry_json = json.dumps(entry_for_hash, ensure_ascii=False, sort_keys=True)
    bad["hash"] = _sha256(bad["prev_hash"] + entry_json)
    lines[1] = json.dumps(bad, ensure_ascii=False, sort_keys=True)
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify(trace)
    assert result is False
    assert "TAMPERED" in capsys.readouterr().out
