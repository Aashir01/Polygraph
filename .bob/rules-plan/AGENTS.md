# Project Architecture Rules (Plan Mode)

- The data pipeline is append-only: `hooks/dump_event.py` → `~/.polygraph_private/raw_events.jsonl` → `polygraph/` processing → `models/`. Never modify raw events in place.
- `polygraph/` (ML/verification logic) and `hooks/` (Bob integration) are intentionally decoupled — hooks must not import from `polygraph` to keep cold-start latency low.
- The dashboard (`dashboard/`) reads from processed outputs, never from `data/raw/` or the live JSONL log directly.
- New features that add Bob hook events must update `.bob/settings.json`; remember `UserPromptSubmit` and `Stop` do not accept a `matcher` field.
