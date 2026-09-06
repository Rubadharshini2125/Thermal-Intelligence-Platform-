import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { COLORS } from '../services/constants'

function FitBounds({ detections }) {
  const map = useMap()
  useEffect(() => {
    if (detections.length === 0) return
    map.fitBounds(
      detections.map((d) => [d.latitude, d.longitude]),
      { padding: [40, 40], maxZoom: 10 },
    )
  }, [detections, map])
  return null
}

export default function MapView({ detections, selectedId, onSelect, isLive }) {
  return (
    <>
      <MapContainer center={[23, 79]} zoom={5} className="map-container" scrollWheelZoom>
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {detections.map((d) => (
          <CircleMarker
            key={d.id}
            center={[d.latitude, d.longitude]}
            radius={d.risk_level === 'High' ? 10 : 7}
            pathOptions={{
              color: d.id === selectedId ? '#ffffff' : COLORS[d.classification] || COLORS.Unknown,
              fillColor: COLORS[d.classification] || COLORS.Unknown,
              fillOpacity: 0.85,
              weight: d.id === selectedId ? 3 : 1.5,
            }}
            eventHandlers={{ click: () => onSelect(d.id) }}
          >
            <Popup>
              <div className="popup">
                {isLive && <div className="popup-live-tag">🔴 NASA FIRMS LIVE DETECTION</div>}
                <strong>{d.classification}</strong>
                <br />
                Risk: {d.risk_level.toUpperCase()} · {d.risk_score}/100
                <br />
                Confidence: {d.confidence ?? 'n/a'}
                <br />
                FRP: {d.frp ?? 'n/a'} MW
                <br />
                Temperature: {d.brightness_temperature ?? 'n/a'} K
                <br />
                Industrial distance: {d.industrial_proximity != null ? `${d.industrial_proximity} km` : 'n/a'}
                <br />
                Persistence: {d.persistence ? 'Yes' : 'No'}
                <br />
                Detection time: {d.timestamp}
                <br />
                Satellite/source: {d.satellite}
              </div>
            </Popup>
          </CircleMarker>
        ))}
        <FitBounds detections={detections} />
      </MapContainer>
      <div className="legend">
        {Object.entries(COLORS).map(([label, color]) => (
          <span key={label}>
            <i style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </>
  )
}
