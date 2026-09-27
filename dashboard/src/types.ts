/** Shared TypeScript types for the dashboard data model. */

export interface TestResult {
  passed: number | null
  failed: number | null
  errors: number | null
  ok: boolean | null
  output: string | null
}

export interface IntegrityResult {
  ok: boolean | null
  flags: unknown[]
}

export interface TraceResult {
  ok: boolean | null
  testAfterEdit: boolean | null
  fullSuiteRun: boolean | null
  lastSrcEditTs: string | null
  lastTestRunTs: string | null
  flags: unknown[]
}

export interface ClaimSentence {
  sentence: string
  verdict: 'SUPPORTED' | 'NOT_SUPPORTED'
}

export interface ClaimResult {
  ok: boolean | null
  source: string | null
  text: string | null
  sentences: ClaimSentence[]
}

export type Verdict = 'VERIFIED' | 'NEEDS_REVIEW' | 'REJECTED' | 'SKIPPED' | 'UNKNOWN'

export interface Run {
  id: string
  ticket: string
  gate: string
  verdict: Verdict
  ts: string | null
  tests: TestResult
  integrity: IntegrityResult
  trace: TraceResult
  claim: ClaimResult
}

export interface KPIs {
  tasksAudited: number
  claimsRejected: number
  blockedCommits: number
  gateOffSlipped: number
}

export interface ChartDataPoint {
  ticket: string
  gateOffPassed: number
  gateOffFailed: number
  gateOnPassed: number
  gateOnFailed: number
  gateOffVerdict: Verdict | null
  gateOnVerdict: Verdict | null
}

export interface CsvRow {
  ticket: string
  gate: string
  bob_claimed_success: string
  verdict: string
  committed: string
  fixed_after_block: string
  [key: string]: string
}

export interface DashboardData {
  generatedAt: string
  kpis: KPIs
  runs: Run[]
  csvRows: CsvRow[]
  chartData: ChartDataPoint[]
}
