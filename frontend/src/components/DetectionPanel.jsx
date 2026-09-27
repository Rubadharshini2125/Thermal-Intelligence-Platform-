 export default function DetectionPanel({ detection, isLive }) {
  if (!detection) return <div className="panel empty">Select a detection on the map for details.</div>
  const d = detection
  return (
    <div className="panel detection-panel">
      {isLive && <div className="popup-live-tag">🔴 NASA FIRMS LIVE DETECTION</div>}
      <div className="panel-header">
        <span className="badge">{d.id}</span>
        <h3>
          {d.classification === 'Industrial Fire' ? '🔥 ' : ''}
          {d.classification}
        </h3>
      </div>
      <div className={`risk-banner risk-${d.risk_level.toLowerCase()}`}>
        {d.risk_level.toUpperCase()} — {d.risk_score}/100 <span style={{ fontWeight: 400, fontSize: 11 }}>(Prototype Risk Score)</span>
      </div>
      <dl className="fact-grid">
        <dt>Thermal intensity</dt>
        <dd>
          {d.frp != null ? `${d.frp} MW FRP` : 'n/a'}
          {d.brightness_temperature != null ? ` · ${d.brightness_temperature} K` : ''}
        </dd>
        <dt>Persistence</dt>
        <dd>{d.persistence ? `Detected across ${d.active_days} observation days` : 'Not persistent'}</dd>
        <dt>Industrial proximity</dt>
        <dd>{d.industrial_proximity != null ? `${d.distance_label} · ${d.nearby_facility}` : 'No facility coverage'}</dd>
        <dt>Confidence</dt>
        <dd>
          {d.confidence != null ? `${d.confidence}%` : 'n/a'} · evidence {d.evidence_score}/100
        </dd>
        <dt>Timestamp (UTC)</dt>
        <dd>{d.timestamp}</dd>
        <dt>Satellite/source</dt>
        <dd>{d.satellite}</dd>
      </dl>
      <h4>Why {d.risk_level === 'High' ? 'high' : 'this'} risk?</h4>
      <ul className="reasons">
        {d.explanation.length ? d.explanation.map((line, i) => <li key={i}>✓ {line}</li>) : <li>No elevated-risk criteria met.</li>}
      </ul>
      <p className="risk-factors">{d.risk_factors}</p>
    </div>
  )
}
