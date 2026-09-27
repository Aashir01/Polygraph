# Project Documentation Rules (Ask Mode)

- Raw event data accumulates in `~/.polygraph_private/raw_events.jsonl` (outside the repo) — this is intentional; the file never appears in git status.
- The `demo_repo/` folder is a synthetic git repository used as a test fixture, not a real sub-project.
- `dashboard/` is a Streamlit app; run with `streamlit run dashboard/app.py` from the project root.
- Hook behaviour reference: `.bob/settings.json` is the source of truth for which events fire and which script handles them.
