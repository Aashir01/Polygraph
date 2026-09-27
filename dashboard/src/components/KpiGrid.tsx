import { type KPIs } from '../types'

interface Props {
  kpis: KPIs
}

const tiles = [
  { key: 'tasksAudited',   label: 'Tasks Audited',           color: 'blue'  },
  { key: 'claimsRejected', label: 'Claims Rejected',          color: 'red'   },
  { key: 'blockedCommits', label: 'Commits Blocked by Gate',  color: 'amber' },
  { key: 'gateOffSlipped', label: 'Slipped Through (Gate Off)', color: 'amber' },
] as const

export default function KpiGrid({ kpis }: Props) {
  return (
    <div className="kpi-grid">
      {tiles.map(t => (
        <div key={t.key} className={`kpi-tile kpi-tile--${t.color}`}>
          <div className="kpi-tile__value">{kpis[t.key]}</div>
          <div className="kpi-tile__label">{t.label}</div>
        </div>
      ))}
    </div>
  )
}
