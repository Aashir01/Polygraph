---
name: polygraph-audit
description: >-
  Use when auditing whether an agent's "done" claim for a demo_repo task is
  actually correct.  Runs the Polygraph verdict engine, shows the evidence
  card, and -- if the verdict is not VERIFIED -- spawns a blind verifier
  sub-agent that derives independent pytest tests from the ticket spec and
  runs them against the current code.  Triggers: audit, verify claim,
  polygraph, check if done, is it really fixed, blind verifier.
---

# Polygraph Audit

Follow these steps in order.  Use `update_todo_list` to track progress.

---

## Step 1 -- Identify the ticket

Ask the user which ticket to audit if it is not already clear from context.
Ticket files live in `demo_repo/tickets/`.  Read the ticket file now so you
have the expected behavior in scope:

```
read_file("demo_repo/tickets/<ticket>.md")
```

If the user names a ticket without the `.md` extension, append it.  If no
ticket is named, list `demo_repo/tickets/` and ask.

---

## Step 2 -- Run the Polygraph verdict engine

Execute:

```
python -m polygraph.verdict
```

Capture stderr (it prints `[polygraph] verdict: <VERDICT>`).  The engine
writes three artefacts:

- `.polygraph/verdict.json`  -- structured result
- `.polygraph/report.md`     -- evidence card
- `~/.polygraph_private/latest_verdict.json` -- private copy

Read `.polygraph/report.md` and display its full contents verbatim so the
user sees every ✓/⚠/✗ line.

If the engine exits non-zero due to an import error or missing baseline tag,
report the error and stop -- do not continue to Step 3.

---

## Step 3 -- Decide whether a blind verifier is needed

Read `.polygraph/verdict.json`.  Check the `"verdict"` field.

- **`"VERIFIED"`** -- the audit is complete.  Report VERIFIED with a one-line
  summary.  Skip Steps 4-6.
- **`"SKIPPED"`** -- demo_repo has not changed from the baseline tag.  Report
  this to the user and stop.
- **`"NEEDS_REVIEW"` or `"REJECTED"`** -- continue to Step 4.

---

## Step 4 -- Spawn the blind verifier sub-agent

Spawn a sub-agent using `spawn_subagent` with **`fork_context: false`** (the
sub-agent must be blind to the conversation and diff).

Build the sub-agent description as follows -- substitute `<ticket_content>`
with the verbatim text of the ticket file you read in Step 1, and
`<ticket_slug>` with the bare ticket name (e.g. `01`):

```
You are an independent test engineer.  You have NOT seen the agent's
implementation, their conversation, or any diff.  Your only input is the
ticket specification below.

TICKET
------
<ticket_content>
------

Your task:
1. Create the directory verifier_tests/<ticket_slug>/ if it does not exist.
2. Write pytest tests in verifier_tests/<ticket_slug>/test_verify.py that
   exercise ONLY the behavior described in the ticket's "Expected Behavior"
   and "Steps to Reproduce" sections.  Import from demo_repo/shop/ using
   sys.path manipulation (sys.path.insert(0, "demo_repo")).  Do NOT copy
   or reference any existing test files.
3. Run your tests with:
       python -m pytest verifier_tests/<ticket_slug>/ -v --tb=short
   Capture the full output.
4. Return a JSON summary on the last line of your response in this exact
   format (no trailing comma, valid JSON):
   {"passed": <int>, "failed": <int>, "errors": <int>, "output": "<last 2000 chars of pytest stdout>"}
```

Do NOT set `fork_context: true` -- the sub-agent must derive tests purely
from the ticket, not from anything in this conversation.

---

## Step 5 -- Parse the verifier result

Extract the JSON summary from the last line of the sub-agent's response.
If no valid JSON is found on the last line, scan backwards for the first
line that parses as JSON with keys `passed`, `failed`, `errors`.

Compute:
- `total = passed + failed + errors`
- `verifier_ok = (failed == 0 and errors == 0)`

---

## Step 6 -- Append the verifier block to the report

Append the following block to `.polygraph/report.md` using `insert_content`
at line 0 (append mode):

```markdown

---

## Blind Verifier Result

**Ticket:** <ticket_slug>
**Tests written independently from ticket spec.**

| Result | Count |
|---|---|
| Passed | <passed> |
| Failed | <failed> |
| Errors | <errors> |

**Verifier verdict:** <PASS if verifier_ok else FAIL>

<details>
<summary>pytest output</summary>

```
<output>
```

</details>
```

Also write `verifier_tests/<ticket_slug>/result.json` with the raw summary
dict plus a `"verifier_ok"` key.

---

## Step 7 -- Final report

Print a concise audit summary to the user:

```
Polygraph Audit - <ticket_slug>
================================
Polygraph verdict : <VERIFIED|NEEDS_REVIEW|REJECTED>
Blind verifier    : <PASS|FAIL> (<passed>/<total> tests)

<one-sentence interpretation, e.g.:
  "The original tests pass but the test suite was never run after the last
   source edit, and the blind verifier finds 1 failure -- the fix is
   incomplete.">

Full evidence: .polygraph/report.md
```

Do not add encouragement or filler.  State only what the evidence shows.
