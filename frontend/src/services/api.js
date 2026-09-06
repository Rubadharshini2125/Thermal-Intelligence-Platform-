const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api'

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

function toQuery(filters) {
  const params = new URLSearchParams()
  ;(filters.classification || []).forEach((c) => params.append('classification', c))
  ;(filters.risk || []).forEach((r) => params.append('risk', r))
  if (filters.persistence !== null && filters.persistence !== undefined) params.set('persistence', filters.persistence)
  if (filters.nearFacility !== null && filters.nearFacility !== undefined) params.set('near_facility', filters.nearFacility)
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  return params.toString()
}

export const api = {
  health: () => request('/health'),
  config: () => request('/config'),
  detections: (filters = {}) => request(`/detections?${toQuery(filters)}`),
  detection: (id) => request(`/detections/${encodeURIComponent(id)}`),
  analytics: (filters = {}) => request(`/analytics?${toQuery(filters)}`),
  analyze: (body) =>
    request('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  exportUrl: (filters = {}) => `${API_BASE}/detections/export?${toQuery(filters)}`,
}
