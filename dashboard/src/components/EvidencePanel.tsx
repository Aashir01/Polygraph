import { type Run } from '../types'
import VerdictBadge from './VerdictBadge'

interface Props {
  run: Run
  onClose: () => void
}

function EvLine({
  icon, label, detail, variant,
}: {
  icon: string
  label: string
  detail?: string
  variant: 'ok' | 'warn' | 'fail'
}) {
  return (
    <div className="ev-line">
      <span className={`ev-line__icon ev-line__icon--${variant}`}>{icon}</span>
      <div>
        <div className="ev-line__label">{label}</div>
        {detail && <div className="ev-line__detail">{detail}</div>}
      </div>
    </div>
  )
}

function ok2variant(ok: boolean | null): 'ok' | 'warn' | 'fail' {
  if (ok === true) return 'ok'
  if (ok === false) return 'fail'
  return 'warn'
}

function ok2icon(ok: boolean | null): string {
  if (ok === true) return '✓'
  if (ok === false) return '✗'
  return '⚠'
}

export default function EvidencePanel({ run, onClose }: Props) {
  const { claim, tests, integrity, trace } = run

  // chain integrity: if trace.ok === false it implies tampered, otherwise valid
  const chainOk = trace.ok !== false
  const chainLabel = chainOk ? 'VALID' : 'TAMPERED'

  return (
    <div className="evidence-panel">
      <div className="evidence-panel__header">
        <div className="evidence-panel__header-title">
          Evidence — SHOP-{run.ticket}&nbsp;
          <VerdictBadge verdict={run.verdict} />
        </div>
        <button className="evidence-panel__close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <div className="evidence-panel__body">

        {/* ── Claim sentences ── */}
        {claim.sentences.length > 0 && (
          <div>
            <div className="ev-section__title">Agent's Claim</div>
            {claim.sentences.map((s, i) => (
              <div
                key={i}
                className={`claim-sentence claim-sentence--${s.verdict.toLowerCase()}`}
              >
                <span className="claim-sentence__icon">
                  {s.verdict === 'SUPPORTED' ? '✓' : '✗'}
                </span>
                <span>
                  <span className={`badge ${s.verdict === 'SUPPORTED' ? 'badge--verified' : 'badge--rejected'}`} style={{ marginRight: 6 }}>
                    {s.verdict.replace('_', ' ')}
                  </span>
                  {s.sentence}
                </span>
              </div>
            ))}
            {claim.sentences.length === 0 && (
              <div className="text-muted text-sm">No claim sentences recorded.</div>
            )}
          </div>
        )}

        {/* ── Evidence lines ── */}
        <div>
          <div className="ev-section__title">Evidence</div>

          <EvLine
            icon={ok2icon(tests.ok)}
            variant={ok2variant(tests.ok)}
            label={`Independent tests: ${tests.passed ?? '?'} passed, ${tests.failed ?? '?'} failed`}
            detail={tests.ok ? 'All original assertions pass.' : 'Original assertions failed — fix is incomplete.'}
          />

          <EvLine
            icon={ok2icon(integrity.ok)}
            variant={ok2variant(integrity.ok)}
            label="Test integrity"
            detail={
              integrity.ok
                ? 'No deleted asserts, skips, or commented-out checks.'
                : `Flags: ${integrity.flags.map(f => JSON.stringify(f)).join(', ')}`
            }
          />

          <EvLine
            icon={ok2icon(trace.testAfterEdit)}
            variant={trace.testAfterEdit ? 'ok' : 'warn'}
            label="Test run after last source edit"
            detail={
              trace.lastSrcEditTs
                ? `Last edit ${trace.lastSrcEditTs.slice(0, 19).replace('T', ' ')}; last test ${trace.lastTestRunTs?.slice(0, 19).replace('T', ' ') ?? '—'}`
                : undefined
            }
          />

          <EvLine
            icon={trace.fullSuiteRun ? '✓' : '⚠'}
            variant={trace.fullSuiteRun ? 'ok' : 'warn'}
            label="Full suite run"
            detail={trace.fullSuiteRun ? undefined : 'Only partial test suite was run.'}
          />
        </div>

        {/* ── Test output ── */}
        {tests.output && (
          <div>
            <div className="ev-section__title">Original Tests Output</div>
            <pre className="test-output">{tests.output}</pre>
          </div>
        )}

        {/* ── Test-integrity flags ── */}
        {!integrity.ok && integrity.flags.length > 0 && (
          <div>
            <div className="ev-section__title">Test-Integrity Findings</div>
            {integrity.flags.map((f, i) => (
              <div key={i} className="flag-list">{JSON.stringify(f)}</div>
            ))}
          </div>
        )}

        {/* ── Log integrity ── */}
        <div>
          <div className="ev-section__title">Log Integrity</div>
          <span className={`integrity-badge integrity-badge--${chainOk ? 'valid' : 'tampered'}`}>
            {chainOk ? '✓' : '✗'} {chainLabel}
          </span>
        </div>

      </div>
    </div>
  )
}
