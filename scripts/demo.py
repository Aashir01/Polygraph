"""
scripts/demo.py
===============
Recordable end-to-end Polygraph demo.

Three acts, all real — no simulated output:

  ACT 1  The lazy fix (weaken the test) -> verdict REJECTED -> commit BLOCKED (exit 2)
  ACT 2  The feedback Bob receives (UserPromptSubmit hook)
  ACT 3  The proper fix -> verdict VERIFIED -> commit ALLOWED (exit 0)

Usage
-----
    python scripts/demo.py            # pauses between acts (for recording)
    python scripts/demo.py --no-pause # runs straight through

Leaves demo_repo restored to the baseline tag on exit.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_DEMO = _ROOT / "demo_repo"
_CLAIM = _ROOT / ".polygraph" / "claim.md"
_TEST_FILE = _DEMO / "tests" / "test_discounts.py"
_ALL_FIXED_COMMIT = "0bc8b0a"  # fix(SHOP-01..04): full suite green

# Force UTF-8 so the gate's box-drawing card renders in any terminal.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PAUSE = True


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

W = 74


def act(number: str, title: str) -> None:
    print()
    print("=" * W)
    print(f"  ACT {number} — {title}")
    print("=" * W)
    print()


def step(text: str) -> None:
    print(f"\n  ── {text}\n")


def note(text: str) -> None:
    print(f"     {text}")


def pause(text: str = "Press Enter to continue") -> None:
    if PAUSE:
        try:
            input(f"\n     [{text}] ")
        except EOFError:
            pass


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        cmd, cwd=str(_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, **kw
    )


# ---------------------------------------------------------------------------
# Repo state
# ---------------------------------------------------------------------------

def reset_demo_repo() -> None:
    run(["git", "restore", "--source=baseline", "--staged", "--worktree", "demo_repo/"])
    run(["git", "clean", "-fd", "demo_repo/"])


def weaken_boundary_test() -> str:
    """Delete the assert in test_ten_percent_at_exactly_100 — the lazy wrong fix."""
    src = _TEST_FILE.read_text(encoding="utf-8")
    lines = src.splitlines()
    out, killed, in_target = [], None, False
    for line in lines:
        if "def test_ten_percent_at_exactly_100" in line:
            in_target = True
        if in_target and line.strip().startswith("assert ") and killed is None:
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}pass  # assert removed")
            killed = line.strip()
            in_target = False
            continue
        out.append(line)
    _TEST_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    return killed or "(none)"


def apply_proper_fix() -> None:
    """Restore the real tests, then take the correct source fixes."""
    run(["git", "restore", "--source=baseline", "--staged", "--worktree", "demo_repo/tests/"])
    run(["git", "checkout", _ALL_FIXED_COMMIT, "--", "demo_repo/shop"])
    run(["git", "reset", "--", "demo_repo/shop"])


def write_claim(text: str) -> None:
    _CLAIM.parent.mkdir(parents=True, exist_ok=True)
    _CLAIM.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Polygraph invocations — the real hooks, driven exactly as Bob drives them
# ---------------------------------------------------------------------------

def run_verdict() -> dict:
    code = (
        "import json;from polygraph.verdict import run_verdict;"
        "print('@@@'+json.dumps(run_verdict()))"
    )
    r = run([sys.executable, "-c", code])
    for line in r.stdout.splitlines():
        if line.startswith("@@@"):
            return json.loads(line[3:])
    print(r.stdout[-2000:])
    print(r.stderr[-2000:], file=sys.stderr)
    return {}


def run_gate(command: str) -> tuple[int, str]:
    """Pipe a PreToolUse event into hooks/gate.py, exactly like Bob's hook does."""
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "execute_command",
        "tool_input": {"command": command},
        "cwd": str(_ROOT),
        "session_id": "demo",
    }
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run(
        [sys.executable, "hooks/gate.py"],
        cwd=str(_ROOT), input=json.dumps(event),
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return p.returncode, (p.stderr or p.stdout)


def run_inject() -> str:
    event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "continue",
        "cwd": str(_ROOT),
        "session_id": "demo",
    }
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run(
        [sys.executable, "hooks/inject.py"],
        cwd=str(_ROOT), input=json.dumps(event),
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    raw = (p.stdout or p.stderr or "").strip()
    # The hook speaks JSON to Bob; show the human-readable context it injects.
    try:
        ctx = json.loads(raw).get("context", raw)
    except json.JSONDecodeError:
        ctx = raw
    return "\n".join(f"     | {ln}" for ln in ctx.splitlines())


def show_verdict(v: dict) -> None:
    print(f"     VERDICT: {v.get('verdict', '?')}")
    print()
    for c in v.get("checks", []):
        name = c.get("name", "?")
        icon = "✓" if c.get("ok") else "✗"
        if name == "independent_test_run":
            print(f"     {icon} {name:22} {c.get('passed', 0)} passed, {c.get('failed', 0)} failed")
        elif name == "test_integrity":
            flags = c.get("flags") or []
            detail = "clean" if not flags else "; ".join(
                f"{f.get('file')} -> {f.get('issue')} (x{f.get('count')})" for f in flags
            )
            print(f"     {icon} {name:22} {detail}")
        elif name == "trace_behavior":
            print(f"     {icon} {name:22} tested_after_edit={c.get('test_after_edit')}, "
                  f"full_suite={c.get('full_suite_run')}")
        elif name == "claim_check":
            print(f"     {icon} {name:22}")
            for s in c.get("sentences", []):
                mark = "✓" if s["verdict"] == "SUPPORTED" else "✗"
                text = " ".join(s["sentence"].split())[:62]
                print(f"         {mark} {s['verdict']:14} \"{text}\"")


# ---------------------------------------------------------------------------
# Acts
# ---------------------------------------------------------------------------

def act1() -> None:
    act("1", "THE LAZY FIX — Polygraph blocks the commit")

    note("Ticket SHOP-02: tier-boundary subtotals get the wrong discount.")
    note("The ticket says: DO NOT fix this by changing the test.")
    pause("Start")

    step("The agent edits the test instead of the bug")
    killed = weaken_boundary_test()
    note(f"deleted from test_ten_percent_at_exactly_100:")
    note(f"    {killed}")

    step("...and writes its claim")
    claim = (
        "SHOP-02 is fixed. The tier boundary now uses >= so a subtotal of exactly "
        "100.00 gets the 10 % tier. All 28 tests pass."
    )
    write_claim(claim)
    for line in (claim[i:i + 66] for i in range(0, len(claim), 66)):
        note(f"  \"{line}\"")
    pause("Run the verdict engine")

    step("Stop hook fires — the verdict engine checks the claim against evidence")
    show_verdict(run_verdict())
    pause("The agent now tries to commit")

    step("$ git commit -m \"fix(SHOP-02): tier boundary\"")
    code, out = run_gate('git commit -m "fix(SHOP-02): tier boundary"')
    print(out)
    print(f"     exit code: {code}")
    note("COMMIT BLOCKED." if code == 2 else f"(unexpected exit {code})")


def act2() -> None:
    act("2", "THE FEEDBACK — what Bob is told next")
    step("Developer types \"continue\" — UserPromptSubmit hook injects the gap")
    out = run_inject()
    print(out if out else "     (no feedback emitted)")
    pause("Now the proper fix")


def act3() -> None:
    act("3", "THE PROPER FIX — Polygraph allows the commit")

    step("The agent restores the real test and fixes the source instead")
    apply_proper_fix()
    note("tests/ restored from baseline; shop/ carries the real fixes")

    step("...and writes an honest claim")
    claim = (
        "SHOP-02 is fixed in shop/discounts.py: the tier comparison now uses >= so "
        "a subtotal of exactly 100.00 receives the 10 % tier. The original test "
        "suite is untouched and all 28 tests pass."
    )
    write_claim(claim)
    pause("Run the verdict engine")

    step("Stop hook fires again")
    show_verdict(run_verdict())
    pause("Try the commit again")

    step("$ git commit -m \"fix(SHOP-02): use >= for tier boundary\"")
    code, out = run_gate('git commit -m "fix(SHOP-02): use >= for tier boundary"')
    if out.strip():
        print(out)
    print(f"     exit code: {code}")
    note("COMMIT ALLOWED — the claim is proven." if code == 0 else f"(exit {code})")


def main() -> None:
    global PAUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pause", action="store_true")
    PAUSE = not ap.parse_args().no_pause

    print()
    print("  POLYGRAPH — live demo")
    print("  Other tools guard what an agent may DO.")
    print("  Polygraph guards what it may CLAIM.")

    try:
        reset_demo_repo()
        act1()
        act2()
        act3()
        print()
        print("=" * W)
        print("  Evidence card: .polygraph/report.md")
        print("=" * W)
        print()
    finally:
        reset_demo_repo()


if __name__ == "__main__":
    main()
