# Polygraph Dashboard

A static developer-tool dashboard that visualises every Polygraph audit run, evidence card, and gate experiment.

## Requirements

- Node.js 18+

## Quick start

```bash
cd dashboard
npm install

# Bundle data from dashboard/data/*.json + experiment/results.csv
npm run data

# Development server (hot-reload, no data re-bundle on change)
npm run dev

# Production build → dashboard/dist/
npm run build

# Preview the production build locally
npm run preview
```

The `build` script runs `npm run data` first, so `dist/` always contains fresh data.

## Adding new audit runs

1. Copy the `.polygraph/verdict.json` produced by the verdict engine into `dashboard/data/`.
   Name the file `t<ticket>_<gate>.json` — e.g. `t03_on.json`.
2. Optionally append a row to `experiment/results.csv`.
3. Re-run `npm run build` (or just `npm run data` during development).

## Directory layout

```
dashboard/
  data/            Verdict JSON files (one per audit run)
  public/          Static assets; data.json is generated here
  scripts/
    bundle-data.mjs  Node script that merges data sources → public/data.json
  src/
    App.tsx          Root component
    components/      KpiGrid, Pipeline, ReviewTable, EvidencePanel, ExperimentChart
    index.css        Global CSS with CSS variables (light + dark mode)
    types.ts         Shared TypeScript interfaces
  index.html
  package.json
  tsconfig.json
  vite.config.ts
```

## Design notes

- **No UI framework** — plain CSS with `--css-variable` theming.
- **Fonts** — Inter (UI) and JetBrains Mono (code, verdicts, file names) via Google Fonts.
- **Dark mode** — fully supported via `@media (prefers-color-scheme: dark)`.
- **Charts** — Recharts grouped bar chart comparing Gate OFF vs Gate ON per ticket.
- **Responsive** — works on mobile widths; the table + evidence panel stack vertically below 900 px.
