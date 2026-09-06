export default function Header({ config }) {
  const demo = config?.demo_mode !== false
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-icon">🔥</span>
        <div>
          <h1>Thermal Intelligence Platform</h1>
          <p>NASA FIRMS + OSM + AI-Based Risk Analysis</p>
        </div>
      </div>
      <div className={`mode-badge ${demo ? 'demo' : 'live'}`}>{demo ? 'DEMO MODE' : 'LIVE FIRMS MODE'}</div>
    </header>
  )
}
