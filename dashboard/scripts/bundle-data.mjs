/**
 * dashboard/scripts/bundle-data.mjs
 *
 * Reads every verdict JSON in dashboard/data/ plus experiment/results.csv,
 * merges them, and writes dashboard/public/data.json.
 *
 * Run:  node scripts/bundle-data.mjs  (from the dashboard/ directory)
 *        npm run data
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')          // dashboard/
const REPO_ROOT = path.resolve(ROOT, '..')          // project root
const DATA_DIR = path.join(ROOT, 'data')
// Prefer the live CSV at the repo root; fall back to the copy inside data/ so the
// bundler still works when only dashboard/ is deployed (e.g. Vercel root directory).
const CSV_CANDIDATES = [
  path.join(REPO_ROOT, 'experiment', 'results.csv'),
  path.join(DATA_DIR, 'results.csv'),
]
const CSV_PATH = CSV_CANDIDATES.find(p => fs.existsSync(p)) ?? CSV_CANDIDATES[0]
const OUT_DIR = path.join(ROOT, 'public')
const OUT_FILE = path.join(OUT_DIR, 'data.json')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function safeReadJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    console.warn(`  [warn] Could not parse ${filePath}`)
    return null
  }
}

/**
 * Parse the minimal CSV we have.  Trims whitespace from headers and values.
 * Returns array of objects keyed by trimmed header names.
 */
function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim())
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.trim())
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim())
    const row = {}
    headers.forEach((h, i) => { row[h] = vals[i] ?? '' })
    return row
  })
}

/**
 * Derive a stable run id from the filename, e.g. "t02_off" → { ticket:"02", gate:"off" }
 */
function parseFileName(name) {
  const m = name.match(/^t(\d+)_(on|off)/)
  if (m) return { ticket: m[1], gate: m[2] }
  // fallback
  return { ticket: name, gate: 'unknown' }
}

// ---------------------------------------------------------------------------
// Load verdict JSONs
// ---------------------------------------------------------------------------

const verdictFiles = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'))
console.log(`Found ${verdictFiles.length} verdict file(s): ${verdictFiles.join(', ')}`)

const runs = []

for (const file of verdictFiles) {
  const raw = safeReadJson(path.join(DATA_DIR, file))
  if (!raw) continue

  const slug = file.replace('.json', '')
  const { ticket, gate } = parseFileName(slug)

  // Extract each check by name, gracefully
  const checks = Array.isArray(raw.checks) ? raw.checks : []
  const byName = name => checks.find(c => c.name === name) ?? {}

  const indep = byName('independent_test_run')
  const integ = byName('test_integrity')
  const trace = byName('trace_behavior')
  const claim = byName('claim_check')

  runs.push({
    id: slug,
    ticket,
    gate,
    verdict: raw.verdict ?? 'UNKNOWN',
    ts: raw.ts ?? null,

    // independent test run
    tests: {
      passed: indep.passed ?? null,
      failed: indep.failed ?? null,
      errors: indep.errors ?? null,
      ok: indep.ok ?? null,
      output: typeof indep.output === 'string' ? indep.output.slice(-2000) : null,
    },

    // test integrity
    integrity: {
      ok: integ.ok ?? null,
      flags: Array.isArray(integ.flags) ? integ.flags : [],
    },

    // trace behavior
    trace: {
      ok: trace.ok ?? null,
      testAfterEdit: trace.test_after_edit ?? null,
      fullSuiteRun: trace.full_suite_run ?? null,
      lastSrcEditTs: trace.last_src_edit_ts ?? null,
      lastTestRunTs: trace.last_test_run_ts ?? null,
      flags: Array.isArray(trace.flags) ? trace.flags : [],
    },

    // claim check
    claim: {
      ok: claim.ok ?? null,
      source: claim.claim_source ?? null,
      text: claim.claim_text ?? null,
      sentences: Array.isArray(claim.sentences) ? claim.sentences : [],
    },
  })
}

// Sort: REJECTED first, then NEEDS_REVIEW, then VERIFIED
const ORDER = { REJECTED: 0, NEEDS_REVIEW: 1, VERIFIED: 2, SKIPPED: 3, UNKNOWN: 4 }
runs.sort((a, b) => (ORDER[a.verdict] ?? 9) - (ORDER[b.verdict] ?? 9))

// ---------------------------------------------------------------------------
// Load CSV
// ---------------------------------------------------------------------------

let csvRows = []
if (fs.existsSync(CSV_PATH)) {
  const text = fs.readFileSync(CSV_PATH, 'utf8')
  csvRows = parseCsv(text)
  console.log(`Loaded ${csvRows.length} CSV row(s) from experiment/results.csv`)
} else {
  console.warn(`  [warn] ${CSV_PATH} not found — skipping CSV`)
}

// ---------------------------------------------------------------------------
// Compute KPIs
// ---------------------------------------------------------------------------

const tasksAudited = runs.length
const claimsRejected = runs.filter(r => r.verdict === 'REJECTED').length
const gateOnRuns = runs.filter(r => r.gate === 'on')
const blockedCommits = gateOnRuns.filter(r => r.verdict !== 'VERIFIED').length
const gateOffVerified = runs.filter(r => r.gate === 'off' && r.verdict !== 'VERIFIED').length

const kpis = {
  tasksAudited,
  claimsRejected,
  blockedCommits,
  gateOffSlipped: gateOffVerified,
}

// ---------------------------------------------------------------------------
// Experiment chart data: group by ticket, gate off vs on
// ---------------------------------------------------------------------------

const ticketSet = [...new Set(runs.map(r => r.ticket))].sort()
const chartData = ticketSet.map(ticket => {
  const offRun = runs.find(r => r.ticket === ticket && r.gate === 'off')
  const onRun  = runs.find(r => r.ticket === ticket && r.gate === 'on')
  return {
    ticket: `Ticket ${ticket}`,
    gateOffPassed: offRun?.tests.passed ?? 0,
    gateOffFailed: offRun?.tests.failed ?? 0,
    gateOnPassed:  onRun?.tests.passed ?? 0,
    gateOnFailed:  onRun?.tests.failed ?? 0,
    gateOffVerdict: offRun?.verdict ?? null,
    gateOnVerdict:  onRun?.verdict ?? null,
  }
})

// ---------------------------------------------------------------------------
// Write output
// ---------------------------------------------------------------------------

fs.mkdirSync(OUT_DIR, { recursive: true })

const output = {
  generatedAt: new Date().toISOString(),
  kpis,
  runs,
  csvRows,
  chartData,
}

fs.writeFileSync(OUT_FILE, JSON.stringify(output, null, 2))
console.log(`\nWrote ${OUT_FILE}  (${runs.length} runs, ${csvRows.length} CSV rows)`)
