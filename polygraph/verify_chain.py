"""
polygraph/verify_chain.py
Verifies the integrity of ~/.polygraph_private/trace.jsonl.

Prints VALID if every entry's hash field matches sha256(prev_hash + entry_json)
and the prev_hash chain is unbroken.  Prints TAMPERED (with details) otherwise.

Usage:
    python -m polygraph.verify_chain
    python polygraph/verify_chain.py
"""

import hashlib
import json
import sys
from pathlib import Path

_TRACE = Path.home() / ".polygraph_private" / "trace.jsonl"
_GENESIS = "0" * 64


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def verify(trace_path: Path = _TRACE) -> bool:
    """
    Return True if the chain is intact, False if tampered.

    Each entry must satisfy:
        entry["hash"] == sha256(entry["prev_hash"] + json.dumps(entry_without_hash, sort_keys=True))

    The chain must be contiguous: entry[n]["prev_hash"] == entry[n-1]["hash"].
    """
    if not trace_path.exists():
        print("VALID (empty chain)")
        return True

    expected_prev = _GENESIS
    lines_checked = 0

    with open(trace_path, "r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                print(f"TAMPERED — line {lineno}: invalid JSON ({exc})")
                return False

            stored_hash: str = entry.get("hash", "")
            prev_hash: str = entry.get("prev_hash", "")

            # Check chain linkage
            if prev_hash != expected_prev:
                print(
                    f"TAMPERED — line {lineno}: prev_hash mismatch "
                    f"(expected {expected_prev[:16]}…, got {prev_hash[:16]}…)"
                )
                return False

            # Recompute the hash: remove `hash` field, keep everything else
            entry_for_hash = {k: v for k, v in entry.items() if k != "hash"}
            entry_json = json.dumps(entry_for_hash, ensure_ascii=False, sort_keys=True)
            expected_hash = _sha256_str(prev_hash + entry_json)

            if stored_hash != expected_hash:
                print(
                    f"TAMPERED — line {lineno}: hash mismatch "
                    f"(expected {expected_hash[:16]}…, stored {stored_hash[:16]}…)"
                )
                return False

            expected_prev = stored_hash
            lines_checked += 1

    print(f"VALID ({lines_checked} entries)")
    return True


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
