export default function StatsCards({ analytics }) {
  const cards = [
    ['Total Detections', analytics?.total_detections ?? 0],
    ['Industrial Fires', analytics?.industrial_fires ?? 0],
    ['Persistent Sources', analytics?.persistent_detections ?? 0],
    ['High Risk', analytics?.high_risk_detections ?? 0],
  ]
  return (
    <div className="stats-row">
      {cards.map(([label, value]) => (
        <div className="stat-card" key={label}>
          <div className="stat-value">{value}</div>
          <div className="stat-label">{label}</div>
        </div>
      ))}
    </div>
  )
}
