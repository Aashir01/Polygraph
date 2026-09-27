# Polygraph Verdict Report
**Verdict:** VERIFIED
**Generated:** 2026-09-27T09:45:15.015725+00:00

✓ **Independent Test Run**: 28 passed, 0 failed

✓ **Test Integrity**: clean

✓ **Trace Behavior**: test_after_edit=True, full_suite_run=True

✓ **Claim Check** (source: stop_event):
  - ✓ [SUPPORTED] Build is clean.
  - ✓ [SUPPORTED] Here's everything that was created:

---

## What was built

### Data bundler â€” [`dashboard/scripts/bundle-data.mjs`](dashboard/scripts/bundle-data.mjs)

Node ES-module that reads every `dashboard/data/*.json` and `experiment/results.csv`, normalises fields gracefully (missing fields become `null`), computes the 4 KPIs, sorts runs REJECTED-first, and writes [`dashboard/public/data.json`](dashboard/public/data.json).
  - ✓ [SUPPORTED] Runs as `npm run data`; `build` runs it automatically first.
  - ✓ [SUPPORTED] ### React app â€” `dashboard/src/`

| File | Purpose |
|---|---|
| [`types.ts`](dashboard/src/types.ts) | Shared TS interfaces (`Run`, `Verdict`, `KPIs`, `ChartDataPoint`, â€¦) |
| [`App.tsx`](dashboard/src/App.tsx) | Root â€” fetches `data.json`, wires all sections |
| [`components/KpiGrid.tsx`](dashboard/src/components/KpiGrid.tsx) | 4 KPI tiles with accent-colour left borders |
| [`components/Pipeline.tsx`](dashboard/src/components/Pipeline.tsx) | 4-step horizontal pipeline of Bob hooks |
| [`components/ReviewTable.tsx`](dashboard/src/components/ReviewTable.tsx) | Sortable run table, coloured verdict badges, row click â†’ evidence |
| [`components/EvidencePanel.tsx`](dashboard/src/components/EvidencePanel.tsx) | Side panel: claim sentences (SUPPORTED/NOT SUPPORTED), âœ“/âš /âœ— evidence lines, test output, log-integrity badge |
| [`components/ExperimentChart.tsx`](dashboard/src/components/ExperimentChart.tsx) | Recharts grouped bar chart (gate OFF vs ON) + CSV results table |
| [`index.css`](dashboard/src/index.css) | ~370 lines of plain CSS; full dark/light mode via `@media (prefers-color-scheme: dark)`; Inter + JetBrains Mono |

### Build output

```
dashboard/dist/
  index.html        0.71 kB
  assets/index.css  8.90 kB (gzip 2.25 kB)
  assets/index.js   526 kB  (gzip 152 kB)
```

To run it locally:

```bash
cd dashboard
npm install
npm run build    # bundles data + compiles
npm run preview  # serves dist/ on localhost
```
