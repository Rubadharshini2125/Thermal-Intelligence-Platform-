import { COLORS } from '../services/constants'

function BarList({ title, data, colorFor }) {
  const entries = Object.entries(data)
  const max = Math.max(1, ...entries.map(([, v]) => v))
  return (
    <div className="bar-list">
      <h4>{title}</h4>
      {entries.length === 0 && <p className="risk-factors">No data</p>}
      {entries.map(([label, value]) => (
        <div className="bar-row" key={label}>
          <span>{label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(value / max) * 100}%`, background: colorFor ? colorFor(label) : '#3fa9c9' }} />
          </div>
          <span className="bar-value">{value}</span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsCharts({ analytics }) {
  if (!analytics) return null
  const riskColor = { High: '#e24a3b', Moderate: '#e7a52e', Low: '#4c8c6b' }
  return (
    <section className="analytics-section">
      <h3>Analytics</h3>
      <div className="analytics-grid">
        <BarList title="By classification" data={analytics.by_classification} colorFor={(l) => COLORS[l] || '#3fa9c9'} />
        <BarList title="By risk" data={analytics.by_risk} colorFor={(l) => riskColor[l] || '#3fa9c9'} />
        <BarList title="By acquisition date" data={analytics.by_date} />
      </div>
    </section>
  )
}
