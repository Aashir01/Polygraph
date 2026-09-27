# Polygraph — 8 slides

Speaker notes in italics. Build these in whatever tool is fastest; the content is final.

---

## 1 — Every AI agent says "Done ✅"

> In April 2026, an AI coding agent deleted a company's production database and its
> backups in **9 seconds**.

**Which "dones" are true?**

*Open cold with the incident, then the question. Don't explain the product yet.*

---

## 2 — The problem, in numbers

| | |
|---|---|
| **66%** | of developers say AI code is "almost right, but not quite" — their #1 frustration |
| **29%** | trust AI accuracy (down) |
| **~50%** | of SWE-bench-passing patches wouldn't be merged by real maintainers (METR) |
| **~50%+** | of rollouts show agents gaming tests — deleted asserts, skips, changed expectations |

*Last row is the one judges remember: the agent edits the test, not the bug.*

---

## 3 — Actions vs. claims

| Layer | What it guards | Example |
|---|---|---|
| Pre-action gate | what the agent may **do** | Inbin Gate |
| Diff reviewer | what the code **says** | CodeRabbit, Bob Review |
| **Polygraph** | what the agent may **claim** | this project |

**Nobody was checking the claim. That's the quiet failure.**

---

## 4 — How it works

```
Bob works a ticket
   |  PostToolUse -> hash-chained trace, stored OUTSIDE the workspace
   v
Bob says "Done"
   |  Stop -> verdict engine:
   |    1. ORIGINAL tests (baseline tag) vs current code
   |    2. test-integrity diff: asserts, skips, expected values, tolerances
   |    3. behaviour: tested after last edit? full suite?
   |    4. claim check: every sentence SUPPORTED / NOT SUPPORTED
   |  -> VERIFIED / NEEDS REVIEW / REJECTED + evidence card
   v
Bob runs "git commit"
   |  PreToolUse -> not VERIFIED? exit 2. BLOCKED.
   v
Developer: "continue"
   |  UserPromptSubmit -> missing evidence injected into Bob's context
   v
Bob fixes properly -> VERIFIED -> commit allowed
```

*The one sentence to say out loud: **truth comes from the original tests, not the tests
the agent may have edited.***

---

## 5 — Inside Bob

| Bob feature | How Polygraph uses it |
|---|---|
| Lifecycle hooks | PostToolUse (record), Stop (verdict), PreToolUse (gate), UserPromptSubmit (feedback) |
| Agent mode | built the whole project; the experiment runs are real Agent-mode tasks |
| AGENTS.md rules | Bob runs tests via `pg_test`, writes its claim to `.polygraph/claim.md` |
| Custom mode | "Polygraph Auditor" — read + run only, **no edit rights** |
| Subagent | blind verifier: sees only the ticket, writes its own tests |
| Skill | `polygraph-audit`, reusable in any project |

**Bob is both the builder and the runtime.**

---

## 6 — Live proof

*Screenshot: the blocked commit (exit 2) side by side with the evidence card.*

```
Verdict: REJECTED
  independent_test_run   21 passed, 7 failed
  test_integrity         tests/test_cart.py -> deleted_asserts (1)
  trace_behavior         ok
  claim_check            "SHOP-04 is fixed."  -> NOT SUPPORTED
                         "All 28 tests pass." -> NOT SUPPORTED
```

*Point at the claim check: the mechanical sentences passed, the success sentences didn't.
That's sentence-level lie detection.*

---

## 7 — Results

**3 recorded ticket runs. Bob was honest in all 3 — and one was still rejected.**

| Ticket | Gate | Claimed | Verdict | Independent run | Integrity |
|---|---|---|---|---|---|
| 02 | off | success | **REJECTED** | 24 pass / 4 fail | clean |
| 04 | off | success | **VERIFIED** | 28 / 0 | clean |
| 04 | on | success | **VERIFIED** | 28 / 0 | clean |

- Hand-weakened test → `deleted_asserts` flagged, **REJECTED**
- **10 commit attempts blocked, 0 unproven commits landed**
- Verdict in **~2.9 s** (median of 3)

*The honest-but-rejected row is the strongest slide in the deck. Ticket 02's fix was
correct; the suite still wasn't green. True claim, unshippable work.*

---

## 8 — Roadmap + close

**Today:** Python / pytest, small synthetic demo repo.
**Next:** more languages and frameworks; mutation testing on changed lines; a CI /
GitHub Action gate; team policies; an advisory behaviour-risk model — hard evidence always
decides.

> AI made writing code nearly free. **Trusting it is the new bottleneck.**
>
> **Polygraph: Bob can't ship it until it's proven.**
