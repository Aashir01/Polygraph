import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { type ChartDataPoint, type CsvRow } from '../types'

interface Props {
  chartData: ChartDataPoint[]
  csvRows: CsvRow[]
}

// Color tokens — must work in both light and dark mode via CSS vars
// Recharts doesn't read CSS vars natively, so we use explicit values
// that look good in both themes (the chart background adapts via the container).
const COLORS = {
  offPassed: '#64b5f6',
  offFailed: '#ef5350',
  onPassed:  '#81c784',
  onFailed:  '#ffb74d',
}

export default function ExperimentChart({ chartData, csvRows }: Props) {
  return (
    <div>
      <div className="chart-wrap">
        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: COLORS.offPassed }} />
            Gate OFF — Passed
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: COLORS.offFailed }} />
            Gate OFF — Failed
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: COLORS.onPassed }} />
            Gate ON — Passed
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: COLORS.onFailed }} />
            Gate ON — Failed
          </span>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="ticket"
              tick={{ fontSize: 12, fontFamily: 'var(--font-mono)', fill: 'var(--text-muted)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
              }}
              labelStyle={{ fontWeight: 600, marginBottom: 4 }}
            />
            <Legend wrapperStyle={{ display: 'none' }} />
            <Bar dataKey="gateOffPassed" name="Gate OFF Passed" fill={COLORS.offPassed} radius={[3,3,0,0]} />
            <Bar dataKey="gateOffFailed" name="Gate OFF Failed" fill={COLORS.offFailed} radius={[3,3,0,0]} />
            <Bar dataKey="gateOnPassed"  name="Gate ON Passed"  fill={COLORS.onPassed}  radius={[3,3,0,0]} />
            <Bar dataKey="gateOnFailed"  name="Gate ON Failed"  fill={COLORS.onFailed}  radius={[3,3,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {csvRows.length > 0 && (
        <div className="csv-table-section">
          <div className="section__title" style={{ marginBottom: 12 }}>Experiment Results</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {Object.keys(csvRows[0]).map(h => (
                    <th key={h}>{h.replace(/_/g, ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvRows.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((v, j) => (
                      <td key={j} className="text-mono">{v || '—'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
