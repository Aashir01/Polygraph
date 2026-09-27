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

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_PRIVATE_DIR = Path.home() / ".polygraph_private"
_GATE_OFF = _PRIVATE_DIR / "GATE_OFF"
_OVERRIDE = _PRIVATE_DIR / "override"

_TRIGGER_RE = re.compile(r"git\s+(commit|push)\b|gh\s+pr\s+create")


def _demo_repo_has_changes(cwd: str) -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain", "demo_repo/"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return bool(r.stdout.strip())


def main() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {}

    command: str = (event.get("tool_input") or {}).get("command", "")
    cwd: str = event.get("cwd", ".")

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
            run_verdict()
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
        sys.exit(0)

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
