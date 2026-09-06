import { useCallback, useEffect, useState } from 'react'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import MapView from '../components/MapView'
import StatsCards from '../components/StatsCards'
import DetectionPanel from '../components/DetectionPanel'
import AnalyticsCharts from '../components/AnalyticsCharts'
import LiveControls from '../components/LiveControls'
import { api } from '../services/api'
import { CLASSIFICATIONS, RISK_LEVELS } from '../services/constants'

const LIVE_REFRESH_MS = 5 * 60 * 1000

export default function Dashboard() {
  const [config, setConfig] = useState(null)
  const [detections, setDetections] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('demo')
  const [switching, setSwitching] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [liveError, setLiveError] = useState(null)
  const [filters, setFilters] = useState({
    classification: [...CLASSIFICATIONS],
    risk: [...RISK_LEVELS],
    persistence: null,
    nearFacility: null,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, det, an] = await Promise.all([api.config(), api.detections(filters), api.analytics(filters)])
      setConfig(cfg)
      setMode(cfg.mode)
      setDetections(det.detections)
      setAnalytics(an)
      setError(null)
      return cfg
    } catch (e) {
      setError(e.message || 'Unable to reach the backend')
      return null
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    load()
  }, [load])

  const runAnalyze = useCallback(
    async (body) => {
      setSwitching(true)
      try {
        const cfg = await api.analyze(body)
        setMode(cfg.mode)
        if (body.mode === 'live') {
          if (cfg.demo_mode) {
            setLiveError(cfg.report || 'Live request unavailable.')
          } else {
            setLiveError(null)
            setLastUpdated(new Date())
          }
        } else {
          setLiveError(null)
        }
        await load()
      } catch (e) {
        setLiveError(e.message || 'Unable to reach the backend')
      } finally {
        setSwitching(false)
      }
    },
    [load],
  )

  useEffect(() => {
    if (mode !== 'live') return undefined
    const id = setInterval(() => runAnalyze({ mode: 'live' }), LIVE_REFRESH_MS)
    return () => clearInterval(id)
  }, [mode, runAnalyze])

  const selected = detections.find((d) => d.id === selectedId) || null
  const isLive = config?.demo_mode === false

  return (
    <div className="app-shell">
      <Header config={config} />
      <LiveControls
        config={config}
        mode={mode}
        switching={switching}
        lastUpdated={lastUpdated}
        liveError={liveError}
        count={detections.length}
        onSetDemo={() => runAnalyze({ mode: 'demo' })}
        onSetLive={() => runAnalyze({ mode: 'live' })}
        onRefresh={() => runAnalyze({ mode: 'live' })}
      />
      {error && <div className="error-banner">Backend unreachable — {error}.</div>}
      {!error && config && <div className="source-banner">{config.source} · {config.report}</div>}
      <div className="main-grid">
        <Sidebar filters={filters} setFilters={setFilters} />
        <div className="map-column">
          <MapView detections={detections} selectedId={selectedId} onSelect={setSelectedId} isLive={isLive} />
          <StatsCards analytics={analytics} />
        </div>
        <div className="detail-column">
          <DetectionPanel detection={selected} isLive={isLive} />
          <a className="export-btn" href={api.exportUrl(filters)}>
            ⬇ Export CSV
          </a>
        </div>
      </div>
      <AnalyticsCharts analytics={analytics} />
      {loading && <div className="loading-overlay">Loading…</div>}
    </div>
  )
}
