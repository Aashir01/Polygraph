# Project Coding Rules (Agent Mode)

- `hooks/dump_event.py` must exit 0 in all cases — use try/except around the entire body; stderr is fine for errors but stdout must stay clean (Bob treats non-empty stdout as model context for some events).
- When adding new hook scripts, register them in `.bob/settings.json` following the existing pattern; `UserPromptSubmit` and `Stop` entries must NOT include a `matcher` key.
- Model artefacts belong in `models/`; never pickle to `data/raw/` (that directory is gitignored and should only hold immutable source data).
- The `polygraph` package exports its public API from `polygraph/__init__.py`; add new public symbols there.
- Use `pytest` for all tests; a single test runs with `pytest path/to/test_file.py::test_name`.
