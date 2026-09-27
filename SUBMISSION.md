# lablab submission — copy-paste fields

All numbers below are measured; sources in [experiment/RESULTS.md](experiment/RESULTS.md).

---

## Project title

Polygraph: Bob can't ship it until it's proven

## Short description

A verification gate for AI coding agents, built into IBM Bob. Polygraph checks every
"done" claim against independent evidence and blocks the commit until it's proven.

## Tags

IBM Bob, Developer Tools, Code Review, Testing, AI Agents, AI Safety

## Long description

**Problem.** AI coding agents now write a large share of the code developers ship, and
every one of them ends a task the same way: "Done ✅". Developers can't tell which of
those claims are true. 66% of developers say AI solutions are "almost right, but not
quite" — their top frustration (Stack Overflow 2025, 49,000+ developers). METR found that
roughly half of SWE-bench-passing patches would not be merged by real maintainers. A
September 2026 paper found agents gaming tests in half or more of rollouts for three open
models: deleting assertions, adding skips, changing expected values. A green checkmark no
longer means the code is correct, and human reviewers can't re-check everything.

**Solution.** Polygraph is a verification gate built into IBM Bob with lifecycle hooks.
Other tools guard what an agent is allowed to do. Polygraph guards what it is allowed to
claim.

- A tamper-evident recorder (PostToolUse hook) logs every action Bob takes into a
  hash-chained trace stored outside the workspace, so edits to the log are detectable.
- When Bob finishes (Stop hook), the verdict engine checks the claim against independent
  evidence. It re-runs the ORIGINAL tests from the baseline tag against the current code,
  so edited tests can't fake a pass. It diffs the test files to catch weakened tests
  (deleted asserts, skip/xfail, changed expected values or tolerances). It checks
  behaviour: was anything tested after the last edit, and was the full suite run? And it
  marks each sentence of Bob's claim SUPPORTED or NOT SUPPORTED.
- The verdict is VERIFIED, NEEDS REVIEW or REJECTED, with an evidence card explaining why.
- If Bob tries to git commit or push an unproven change, the commit gate (PreToolUse hook)
  blocks it with exit code 2.
- The feedback hook (UserPromptSubmit) tells Bob exactly which evidence is missing, so it
  can fix the work properly.
- A "Polygraph Auditor" custom mode (read and run only, no edit rights) launches a
  blind-verifier subagent that sees only the original ticket and writes its own tests.
- A dashboard shows the review queue, evidence cards, session timelines and experiment
  results.

**Impact.** We ran the same tickets through Bob with the gate off and on. Bob was honest
in all 3 recorded runs — every claim sentence checked out against the evidence — and
Polygraph proved that automatically in about 3 seconds per task instead of by hand. It
still rejected one of those honest runs: Bob's ticket-02 fix was correct, but the
independent run of the original test suite came back 24 passed / 4 failed, so "done" was
not shippable. When we weakened a test by hand (one assert deleted from test_cart.py),
Polygraph flagged `deleted_asserts`, returned REJECTED, marked exactly the two
success-claiming sentences NOT SUPPORTED, and blocked 5 commit attempts — 0 unproven
commits landed. Across the recorded gate runs: 10 commit attempts blocked, 0 unproven
commits. The end-to-end self-test passes 5/5, including tamper detection — an intact trace
verifies VALID, and a trace with a single altered entry is caught by a hash mismatch, so
the agent cannot rewrite its own history.

**How Bob powers it.** Bob built Polygraph, and Polygraph runs inside Bob. It uses 4
lifecycle hooks (PostToolUse, Stop, PreToolUse, UserPromptSubmit), AGENTS.md rules, a
custom mode, a subagent and a Skill, and Agent mode throughout the build. Every
task-session summary is in `bob_sessions/`.

---

## One-liners

- **One line:** Polygraph stops AI coding agents from shipping work they only claim is done.
- **The analogy:** A polygraph compares what someone says with what the instruments
  measure. Polygraph compares what Bob says ("fixed it, all tests pass") with what
  actually happened.
- **Tagline:** Stop reviewing everything. Review what's lying.

## Positioning

- Pre-action gates (like Inbin Gate) stop dangerous commands.
- Diff reviewers (CodeRabbit, Bob's own Review) check the code.
- **Polygraph checks whether the claim of success is true**, including whether the agent
  touched the tests to make them pass.

These complement each other. Polygraph covers the quiet failure the others miss.

## Business value

- **Who it's for:** any team using AI coding agents, especially with auto-approve or
  unattended tasks.
- **Value:** review effort goes to the claims that aren't proven, and bad fixes are
  blocked before they enter the codebase — less rework, fewer escaped bugs.
- **Market:** AI code tools are about $9.5B in 2026, heading to $22B by 2030 (Research and
  Markets). AI code review alone is about $1.4B (2025), projected at $10.8B by 2034
  (Market Intelo).
- **Model:** open-source core (hooks + CLI), paid team dashboard and org-wide policies,
  priced per verified agent task. A natural fit as a Bob mode, Skill or plugin.

## Judge questions

**"Isn't this Bob's built-in Review?"** Review checks the code changes. Polygraph checks
whether the claim is true: did the agent verify, did it touch the tests, does what it said
match what the log recorded? They work together.

**"Isn't this just a PR reviewer?"** Reviewers read the diff. Polygraph reads the evidence
and the process behind it, and enforces the result at commit time.

**"Can the agent cheat Polygraph?"** The log is hash-chained and stored outside the
workspace; truth comes from the original tests at the baseline tag; overrides need a file
the developer creates in their own terminal.

**"Your best run was rejected even though the agent was honest — isn't that a false
positive?"** No, that's the point. The claim was true and the work still wasn't
shippable. Polygraph gates shippability, not sincerity.

**"Where's the ML model?"** Not trained — we cut it rather than ship a number we didn't
measure. Every verdict here is hard evidence, which is the part that should never be
probabilistic anyway.
