import { useState, useEffect } from 'react'
import { type DashboardData, type Run } from './types'
import KpiGrid from './components/KpiGrid'
import Pipeline from './components/Pipeline'
import ReviewTable from './components/ReviewTable'
import EvidencePanel from './components/EvidencePanel'
import ExperimentChart from './components/ExperimentChart'

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    fetch('./data.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<DashboardData>
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [])

  const selectedRun: Run | null =
    data && selectedId ? (data.runs.find(r => r.id === selectedId) ?? null) : null

  if (error) {
    return (
      <div className="app">
        <div className="container" style={{ paddingTop: 48 }}>
          <p style={{ color: 'var(--accent-red)' }}>Failed to load data.json: {error}</p>
          <p className="text-muted text-sm" style={{ marginTop: 8 }}>
            Run <code className="mono">npm run data</code> to generate it.
          </p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="app">
        <div className="container" style={{ paddingTop: 48, color: 'var(--text-muted)' }}>
          Loading…
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="container">
          <div className="header__inner">
            <h1 className="header__title">
              <span className="header__title-mark" />
              Polygraph
            </h1>
            <p className="header__tagline">Bob can't ship it until it's proven</p>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="container">

          {/* ── KPIs ── */}
          <section className="section">
            <div className="section__title">Overview</div>
            <KpiGrid kpis={data.kpis} />
          </section>

          {/* ── How it works ── */}
          <section className="section">
            <div className="section__title">How It Works</div>
            <Pipeline />
          </section>

          {/* ── Review queue + evidence panel ── */}
          <section className="section">
            <div className="section__title">Review Queue</div>
            <div className={`review-layout ${selectedRun ? 'has-selection' : ''}`}>
              <ReviewTable
                runs={data.runs}
                selectedId={selectedId}
                onSelect={id => setSelectedId(prev => prev === id ? null : id)}
              />
              {selectedRun ? (
                <EvidencePanel run={selectedRun} onClose={() => setSelectedId(null)} />
              ) : (
                <div className="evidence-panel" style={{ display: selectedId ? 'block' : 'none' }}>
                  <div className="empty-panel">Select a row to view the evidence card.</div>
                </div>
              )}
            </div>
          </section>

          {/* ── Experiment ── */}
          <section className="section">
            <div className="section__title">Experiment — Gate Off vs Gate On</div>
            <ExperimentChart chartData={data.chartData} csvRows={data.csvRows} />
          </section>

        </div>
      </main>
    </div>
  )
}
