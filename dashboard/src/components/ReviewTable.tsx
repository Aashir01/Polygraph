import { type Run, type Verdict } from '../types'
import VerdictBadge from './VerdictBadge'

interface Props {
  runs: Run[]
  selectedId: string | null
  onSelect: (id: string) => void
}

function fmt(ts: string | null) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return ts
  }
}

export default function ReviewTable({ runs, selectedId, onSelect }: Props) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Gate</th>
            <th>Verdict</th>
            <th>Tests (pass / fail)</th>
            <th>Claim ok?</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {runs.map(run => (
            <tr
              key={run.id}
              className={selectedId === run.id ? 'selected' : ''}
              onClick={() => onSelect(run.id)}
            >
              <td className="text-mono">SHOP-{run.ticket}</td>
              <td>
                <span className={`badge ${run.gate === 'on' ? 'badge--verified' : 'badge--unknown'}`}>
                  {run.gate.toUpperCase()}
                </span>
              </td>
              <td><VerdictBadge verdict={run.verdict as Verdict} /></td>
              <td className="text-mono">
                {run.tests.passed ?? '?'} / {run.tests.failed ?? '?'}
              </td>
              <td>
                {run.claim.ok === null ? '—' : run.claim.ok ? '✓' : '✗'}
              </td>
              <td className="text-muted text-sm">{fmt(run.ts)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
