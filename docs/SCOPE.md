# Polygraph — Full Scope

A verification gate for AI coding agents, built into IBM Bob with lifecycle hooks.
Other tools guard what an agent may DO; Polygraph guards what it may CLAIM.
When Bob says "done", Polygraph checks the claim against independent evidence
and blocks git commit/push until it is proven.

---

## Core (already exists — verify and fix gaps)

- **Recorder:** PostToolUse hook writes a hash-chained trace to
  `~/.polygraph_private/trace.jsonl`; `verify_chain` prints VALID/TAMPERED;
  `pg_test` wraps pytest and logs runs.

- **Verdict engine (Stop hook):** runs the ORIGINAL tests from git tag "baseline"
  against the current code; test-integrity diff (deleted asserts, skip/xfail,
  commented-out asserts, changed expected values or tolerances); behavior checks
  (test after last edit, full suite run, edit loops); claim check (each claim
  sentence SUPPORTED/NOT SUPPORTED); verdict VERIFIED / NEEDS_REVIEW / REJECTED;
  `.polygraph/report.md` evidence card.

- **Commit gate (PreToolUse):** blocks `git commit` / `git push` / `gh pr create`
  with exit 2 when demo_repo changes are not VERIFIED.

- **Feedback (UserPromptSubmit):** injects the missing evidence into the next prompt.

- **Custom mode "Polygraph Auditor"** (read + command only, no edit) with a
  blind-verifier subagent that sees only the ticket and writes its own tests, plus
  a Skill in `.bob/skills/polygraph-audit/SKILL.md`.

---

## PHASE 1: Experiment Automation CLI

Create `python -m polygraph <command>`:

### `gate on|off|status`
Creates or removes `~/.polygraph_private/GATE_OFF`.

### `run start --ticket <id> --gate <on|off>`
- Resets demo_repo to tag baseline
  (`git restore --source=baseline --staged --worktree demo_repo`,
  then `git clean -fd demo_repo`)
- Commits "reset for run t<id>_<gate>" if anything changed
- Sets the gate mode
- Writes `~/.polygraph_private/active_run.json` with ticket, gate, start time,
  start commit, and the current trace.jsonl line count

### Automatic recording
Whenever the Stop hook or the gate computes a verdict while a run is active,
write `dashboard/data/runs/<run_id>.json` containing:
run_id, ticket, gate, full verdict, claim text, claim sentences with status,
evidence lines, test-integrity findings, original-tests result,
log integrity (verify_chain), this run's trace events (sliced from the start line),
gate block count, whether the agent claimed success, whether a commit touching
demo_repo was made after the start commit, first verdict and final verdict.

Upsert (never duplicate) a row in `experiment/results.csv`:
run_id, ticket, gate, claimed_success, first_verdict, final_verdict,
blocked_count, committed, fixed_after_block, duration_seconds.

The gate also writes a GATE_BLOCK event into the hash-chained trace every time
it blocks.

### `run end`
Finalizes the run and clears active_run.json.

### `run list`
Prints results.csv as a table.

### `selftest`
End-to-end test using simulated hook events (JSON piped to the hook scripts).
Checks:
- (a) A weakened test in demo_repo gives verdict REJECTED and the gate exits 2
  on "git commit"
- (b) No demo_repo changes means the gate allows
- (c) With GATE_OFF the gate allows but the verdict is still recorded
- (d) Editing one trace line makes verify_chain report TAMPERED
- (e) Run files and results.csv are written and upserted

Backs up and restores demo_repo and the trace, prints PASS/FAIL per check.

---

## PHASE 2: Behavior-Risk Model (ML, advisory)

- **Data:** Hugging Face dataset "tarsur385/swev-trm-trajectories-25models"
  (SWE-bench Verified agent trajectories from 25 models, labelled by the official
  harness, task-disjoint train/val splits).  Check the license on the dataset card
  and record name, link and license in `DATA_SOURCES.md`; if it can't be used, try
  "nebius/SWE-agent-trajectories".  Load with the datasets library, keep up to
  ~4000 train rows and the whole val split, cache in `data/raw/` (gitignored).

- **`polygraph/ml/features.py`:** map each step to canonical actions and compute
  ~20 features.  Also `from_trace()`: same features from Bob's `trace.jsonl`.

- **`polygraph/ml/train.py`:** LightGBM with GroupKFold by task id on train, final
  evaluation on val split.  Report ROC-AUC, PR-AUC, and review-budget curve.
  Isotonic calibration.  SHAP top-3 reasons per prediction.
  Save `models/trust_model.pkl`, `models/metrics.json`, `models/feature_importance.json`.

- **Integration:** `verdict.json` and `report.md` gain "behavior_risk" (calibrated
  failure probability) and its top-3 reasons.  Advisory only, never changes verdict.

---

## PHASE 3: Dashboard

`dashboard/` with Vite + React + TypeScript, built as a static site for Vercel.

- **Data bundler:** `dashboard/scripts/bundle-data.mjs` reads run JSONs,
  `experiment/results.csv`, `models/metrics.json`, `models/feature_importance.json`,
  and writes `dashboard/public/data.json`.

- **Views (hash routing):**
  1. `#overview` — KPI tiles + pipeline diagram with animated flow
  2. `#queue` — Review queue table with search, filters, sorting
  3. `#run/<id>` — Polygraph readout: claim sentences, evidence checklist,
     test-integrity diff, session timeline (polygraph chart), behavior-risk gauge
  4. `#experiment` — grouped bar chart gate OFF vs ON, results table
  5. `#model` — metric cards, ROC curve, review-budget curve, feature importances

- **Design:** polished developer-tool look (Linear / Vercel style), dark by default
  with light-mode toggle, one red accent (rejected/blocked), green (verified),
  amber (needs review), responsive, keyboard accessible, real data only.
