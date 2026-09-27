import { type Verdict } from '../types'

const LABELS: Record<Verdict, string> = {
  VERIFIED: 'VERIFIED',
  NEEDS_REVIEW: 'NEEDS REVIEW',
  REJECTED: 'REJECTED',
  SKIPPED: 'SKIPPED',
  UNKNOWN: 'UNKNOWN',
}

const ICONS: Record<Verdict, string> = {
  VERIFIED: '✓',
  NEEDS_REVIEW: '⚠',
  REJECTED: '✗',
  SKIPPED: '–',
  UNKNOWN: '?',
}

interface Props {
  verdict: Verdict
}

export default function VerdictBadge({ verdict }: Props) {
  const cls = `badge badge--${verdict.toLowerCase().replace(' ', '_')}`
  return (
    <span className={cls}>
      <span>{ICONS[verdict]}</span>
      {LABELS[verdict]}
    </span>
  )
}
