import { CLASSIFICATIONS, RISK_LEVELS } from '../services/constants'

function toggle(list, value) {
  const set = new Set(list)
  set.has(value) ? set.delete(value) : set.add(value)
  return [...set]
}

export default function Sidebar({ filters, setFilters }) {
  return (
    <aside className="sidebar">
      <h3>Filters</h3>
      <div className="filter-group">
        <h4>Classification</h4>
        {CLASSIFICATIONS.map((c) => (
          <label key={c} className="checkbox">
            <input
              type="checkbox"
              checked={filters.classification.includes(c)}
              onChange={() => setFilters((f) => ({ ...f, classification: toggle(f.classification, c) }))}
            />
            {c}
          </label>
        ))}
      </div>
      <div className="filter-group">
        <h4>Risk</h4>
        {RISK_LEVELS.map((r) => (
          <label key={r} className="checkbox">
            <input
              type="checkbox"
              checked={filters.risk.includes(r)}
              onChange={() => setFilters((f) => ({ ...f, risk: toggle(f.risk, r) }))}
            />
            {r}
          </label>
        ))}
      </div>
      <div className="filter-group">
        <h4>Persistence</h4>
        <select
          value={filters.persistence === null ? 'all' : String(filters.persistence)}
          onChange={(e) => setFilters((f) => ({ ...f, persistence: e.target.value === 'all' ? null : e.target.value === 'true' }))}
        >
          <option value="all">All</option>
          <option value="true">Persistent</option>
          <option value="false">Non-persistent</option>
        </select>
      </div>
      <div className="filter-group">
        <h4>Industrial proximity</h4>
        <select
          value={filters.nearFacility === null ? 'all' : String(filters.nearFacility)}
          onChange={(e) => setFilters((f) => ({ ...f, nearFacility: e.target.value === 'all' ? null : e.target.value === 'true' }))}
        >
          <option value="all">All</option>
          <option value="true">Near industrial facility</option>
        </select>
      </div>
    </aside>
  )
}
