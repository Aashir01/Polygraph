# Polygraph

**Bob can't ship it until it's proven.**

A verification gate for AI coding agents, built into IBM Bob with lifecycle hooks.
Other tools guard what an agent is allowed to **do**. Polygraph guards what it is
allowed to **claim**.

- Dashboard: https://dashboard-aashir01s-projects.vercel.app
- Demo video: _&lt;add video URL&gt;_
- Bob task-session screenshots: [bob_sessions/](bob_sessions/)

---

## The problem

Every AI coding agent ends a task the same way: **"Done ✅"**. Developers can't tell
which of those claims are true.

- **66%** of developers say AI solutions are "almost right, but not quite" — their top
  frustration; trust in AI accuracy has fallen to **29%** (Stack Overflow Developer
  Survey 2025, 49,000+ developers).
- **~Half** of SWE-bench-passing patches would not be merged by real maintainers (METR).
- Agents **game tests in half or more of rollouts** across three open models — deleting
  assertions, adding skips, changing expected values (paper, Sep 2026).

A green checkmark no longer means the code is correct, and human reviewers cannot
re-check everything.

## What Polygraph does

When Bob says "done", Polygraph checks the claim against **independent evidence** and
blocks `git commit` / `git push` until it is proven.

1. **Tamper-evident recorder** — every tool call Bob makes is logged into a
   hash-chained trace stored *outside* the workspace, so edits to the log are detectable.
2. **Verdict engine** — re-runs the **original tests from the `baseline` git tag**
   against the current code, so edited tests can't fake a pass; diffs the test files for
   weakening (deleted asserts, `skip`/`xfail`, changed expected values or tolerances);
   checks behaviour (was anything tested after the last edit? was the full suite run?);
   and marks **each sentence** of Bob's claim `SUPPORTED` or `NOT_SUPPORTED`.
3. **Verdict** — `VERIFIED` / `NEEDS_REVIEW` / `REJECTED`, with an evidence card
   ([.polygraph/report.md](.polygraph/report.md)) explaining exactly why.
4. **Commit gate** — an unproven commit or push exits with code `2`: blocked.
5. **Feedback** — the missing evidence is injected into Bob's next prompt so it can fix
   the work properly.

> **Tagline:** Stop reviewing everything. Review what's lying.

## Architecture

```
Bob works on a ticket
   |  PostToolUse hook -> Recorder: every action -> hash-chained trace (outside workspace)
   v
Bob says "Done"
   |  Stop hook -> Verdict engine:
   |     1. Original tests (from the baseline tag) vs current code
   |     2. Test-integrity diff (asserts, skips, expected values, tolerances)
   |     3. Behaviour checks (tested after last edit? full suite?)
   |     4. Claim check (each sentence SUPPORTED / NOT_SUPPORTED)
   |  -> VERIFIED / NEEDS_REVIEW / REJECTED + evidence card
   v
Bob runs "git commit"
   |  PreToolUse hook -> Gate: not VERIFIED? -> exit 2 (blocked)
   v
Developer says "continue"
   |  UserPromptSubmit hook -> missing evidence injected into Bob's context
   v
Bob fixes properly -> VERIFIED -> commit allowed
```

| Component | What it does |
|---|---|
| [hooks/record.py](hooks/record.py) | Logs every tool call, hash-chained |
| [polygraph/verify_chain.py](polygraph/verify_chain.py) | Prints `VALID` / `TAMPERED` for the trace |
| [polygraph/pg_test.py](polygraph/pg_test.py) | pytest wrapper that logs every test run, even failing ones |
| [polygraph/verdict.py](polygraph/verdict.py) | The four independent evidence checks and the verdict |
| [hooks/gate.py](hooks/gate.py) | Blocks unproven commits/pushes with exit code 2 |
| [hooks/inject.py](hooks/inject.py) | Tells Bob which evidence is missing |
| [hooks/on_stop.py](hooks/on_stop.py) | Runs the verdict when Bob finishes |
| [polygraph/\_\_main\_\_.py](polygraph/__main__.py) | CLI: `gate on/off/status`, `run start/end/list`, `selftest` |
| [.bob/custom_modes.yaml](.bob/custom_modes.yaml) | "Polygraph Auditor" mode — read + run only, no edit rights |
| [.bob/skills/polygraph-audit/SKILL.md](.bob/skills/polygraph-audit/SKILL.md) | Reusable audit skill + blind-verifier subagent |
| [dashboard/](dashboard/) | React + TypeScript + Vite: review queue, evidence cards, session timelines, experiment |

### Why the agent can't cheat it

- The trace lives **outside the workspace** and is **hash-chained**, so Bob cannot
  quietly rewrite its own history.
- Truth comes from the **original tests at the `baseline` tag**, not the tests Bob may
  have edited.
- A human override exists, but only through a file the developer creates in their own
  terminal.
- The gate **fails open** on an internal error, so a Polygraph crash never blocks a
  developer — it just stops enforcing.

## How IBM Bob powers it

| Bob feature | How Polygraph uses it |
|---|---|
| **Lifecycle hooks** | `PostToolUse` (recorder), `Stop` (verdict), `PreToolUse` (gate), `UserPromptSubmit` (feedback) — wired in [.bob/settings.json](.bob/settings.json) |
| **Agent mode** | Built the whole project; the experiment runs are real Agent-mode tasks |
| **AGENTS.md rules** | Bob runs tests through `pg_test` and writes its claim to `.polygraph/claim.md` |
| **Custom mode** | "Polygraph Auditor" — read + execute + skill + subagent, **no edit group** |
| **Subagent** | Blind verifier that sees only the ticket and writes its own tests |
| **Skill** | `polygraph-audit`, reusable in any project |
| **`/init`** | Project context for Bob |

Bob is both the builder and the runtime: Polygraph was built with Bob, and it lives
inside Bob. Every task-session summary is in [bob_sessions/](bob_sessions/).

## Quick start

```bash
pip install -r requirements.txt

# copy .bob/ and hooks/ into your project, then reload the Bob IDE
python -m polygraph selftest          # end-to-end smoke test
python -m polygraph gate status

# run an experiment ticket
python -m polygraph run start --ticket 02 --gate on
#   ... let Bob work the ticket ...
python -m polygraph run end
python -m polygraph run list
```

Dashboard:

```bash
cd dashboard && npm install && npm run dev
```

## Results

Full measured table: [experiment/RESULTS.md](experiment/RESULTS.md). Headlines, all
measured on this repo:

- Bob was **honest in all 3 recorded ticket runs** — every claim sentence came back
  `SUPPORTED` — and Polygraph proved it automatically instead of by hand.
- Polygraph still **rejected one of those runs**: Bob's ticket-02 fix was correct, but
  the independent run of the original tests was **24 passed / 4 failed**, so "done" was
  not shippable. That is the gate doing its job on an honest agent.
- When a test was **weakened by hand** (one assert deleted from `test_cart.py`), the
  integrity check flagged `deleted_asserts`, the verdict went `REJECTED`, and **5 commit
  attempts were blocked, 0 commits landed**.
- A verdict takes **~2.9 s** (median of 3 runs on the demo repo), versus minutes of
  manual checking per task.
- `python -m polygraph selftest` passes **5/5**, including tamper detection: an intact
  trace verifies `VALID`, and a trace with one altered entry is caught with a hash
  mismatch.

## Limitations

- Python and **pytest only** today.
- The demo repo is small and synthetic.
- `PostToolUse` may not fire when a tool errors — which is why test runs are **also**
  logged independently by `pg_test`.
- The behaviour-risk ML model described in the project scope is **not trained**; nothing
  in the results above uses a model. Every verdict is hard evidence.

## Roadmap

More languages and test frameworks; fine-tuning a behaviour-risk model on real Bob
sessions (advisory only — hard evidence always decides); a calibrated risk-budget slider
(conformal risk control); mutation testing on the changed lines; a CI / GitHub Action
version of the gate; team-wide policies.

## Credits and sources

Citations for every number are in [DATA_SOURCES.md](DATA_SOURCES.md).
Polygraph builds on the AgentLens paper and tool (process analysis of agent sessions)
and on agent-trajectory research (arXiv 2608.30391, 2608.13598). **Inbin Gate** is
complementary pre-action work — it guards what an agent may do; Polygraph guards what it
may claim.
