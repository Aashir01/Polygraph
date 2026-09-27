# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

**Polygraph** — a gate that verifies an AI agent's "done" claims before it can commit.

- **Language:** Python 3
- **Package:** `polygraph/` (importable as `polygraph`)
- **Key dependencies:** pandas, numpy, scikit-learn, lightgbm, shap, datasets, streamlit

## Directory Layout

```
polygraph/       # main Python package
  tests/         # unit tests (test_*.py)
  verify_chain.py  # chain integrity checker
  pg_test.py       # pytest wrapper that logs to the chain
hooks/           # Bob lifecycle hook scripts
demo_repo/       # sample repository used for integration demos
dashboard/       # Streamlit dashboard app
notebooks/       # Jupyter analysis notebooks
models/          # serialised model artefacts
data/raw/        # gitignored raw data (do not commit)
```

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests — ALWAYS use pg_test instead of pytest directly
python -m polygraph.pg_test                                    # full suite
python -m polygraph.pg_test polygraph/tests/                   # directory
python -m polygraph.pg_test polygraph/tests/test_chain.py::test_tamper_middle_line

# Verify trace integrity
python -m polygraph.verify_chain

# Launch dashboard
streamlit run dashboard/app.py
```

**Run tests with `python -m polygraph.pg_test` instead of `pytest`.**

## Hook System

`hooks/record.py` is registered for **all five Bob events** in `.bob/settings.json`.

- Non-PostToolUse events → appended to `~/.polygraph_private/raw_events.jsonl`
- PostToolUse events → normalized entry appended to `~/.polygraph_private/trace.jsonl`

### trace.jsonl entry fields
| Field | Description |
|---|---|
| `ts` | UTC ISO-8601 timestamp |
| `session_id` | Bob session id |
| `tool_name` | Raw Bob tool name |
| `category` | `READ`, `EDIT_SRC`, `EDIT_TEST`, `RUN_TEST`, `RUN_OTHER`, `OTHER` |
| `target` | File path or shell command |
| `file_sha256` | SHA-256 of the file after the edit (null for commands) |
| `prev_hash` | Hash of the previous entry (`"000…0"` for the first) |
| `hash` | `sha256(prev_hash + json.dumps(entry_without_hash, sort_keys=True))` |

### Category rules
- `EDIT_TEST` if `tool_input.path` matches `test_*.py` or contains `/tests/`
- `EDIT_SRC` for other file-edit tools (`write_file`, `apply_diff`, `search_and_replace`, `insert_content`)
- `RUN_TEST` for `execute_command` whose command contains `pytest` or `pg_test`
- `RUN_OTHER` for other `execute_command` calls
- `READ` for read-only tools (`read_file`, `glob`, `grep`, `FindSymbol`, …)

## Code Style

- Follow PEP 8; use 4-space indentation.
- Type-annotate all public functions.
- Keep module imports grouped: stdlib → third-party → local.
- Prefix private helpers with a single underscore.
- Raise explicit exceptions (never `assert` for runtime checks).

## Critical Notes

- `data/raw/` is gitignored — never commit raw data or `.env` files.
- `hooks/record.py` must exit 0 in all cases; stderr is fine for errors, stdout must stay clean.
- `UserPromptSubmit` and `Stop` hooks must NOT have a `matcher` field in `settings.json`.
- `pg_test.py` always exits 0 — it is safe to call in hooks and CI without masking other failures.
- The chain is append-only; never modify or delete lines in `trace.jsonl` (detected by `verify_chain`).
