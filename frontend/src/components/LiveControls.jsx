export default function LiveControls({ config, mode, switching, lastUpdated, liveError, count, onSetDemo, onSetLive, onRefresh }) {
  const isLive = config?.demo_mode === false
  return (
    <div className="live-controls">
      <div className="live-status">
        {isLive ? (
          <span className="live-indicator live">
            🟢 LIVE NASA FIRMS
            <span className="dim"> · Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : '—'}</span>
          </span>
        ) : (
          <span className="live-indicator demo">🟡 DEMO DATA</span>
        )}
        <span className="live-count">{isLive ? 'Live detections' : 'Detections'}: {count}</span>
      </div>
      <div className="live-actions">
        <button className={`mode-btn ${mode === 'demo' ? 'active' : ''}`} onClick={onSetDemo} disabled={switching}>
          Demo Data
        </button>
        <button className={`mode-btn ${mode === 'live' ? 'active' : ''}`} onClick={onSetLive} disabled={switching}>
          Live NASA FIRMS
        </button>
        <button className="refresh-btn" onClick={onRefresh} disabled={switching}>
          {switching ? 'Refreshing…' : '⟳ Refresh Live Data'}
        </button>
      </div>
      {liveError && <div className="live-warning">⚠ NASA FIRMS unavailable — {liveError}</div>}
    </div>
  )
}
