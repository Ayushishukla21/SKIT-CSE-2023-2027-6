import { useEffect, useState } from 'react'
import { getProductHistory } from '../services/api'
import { formatDate } from '../utils/date'

const PLATFORMS = [
  { id: 1, name: 'Blinkit', color: '#e8a33d' },
  { id: 2, name: 'Zepto', color: '#7b2cbf' },
  { id: 3, name: 'Instamart', color: '#e76f51' },
  { id: 4, name: 'Flipkart Minutes', color: '#2d6a4f' }
]

const platformById = (id) => PLATFORMS.find((p) => p.id === id)

function formatPrice(value) {
  return `₹${Number(value).toFixed(2)}`
}

function hasPrice(row) {
  return row.available !== false && row.price != null
}

function HistoryChart({ rows }) {
  const points = rows.filter(hasPrice)
  if (points.length < 2) return null

  const W = 640
  const H = 220
  const pad = { top: 16, right: 16, bottom: 28, left: 52 }
  const times = rows.map((r) => new Date(r.recorded_at).getTime())
  const tMin = Math.min(...times)
  const tMax = Math.max(...times)
  const prices = points.map((r) => Number(r.price))
  let pMin = Math.min(...prices)
  let pMax = Math.max(...prices)
  if (pMin === pMax) {
    pMin -= 1
    pMax += 1
  }
  const x = (t) => pad.left + (tMax === tMin ? 0.5 : (t - tMin) / (tMax - tMin)) * (W - pad.left - pad.right)
  const y = (p) => pad.top + (1 - (p - pMin) / (pMax - pMin)) * (H - pad.top - pad.bottom)

  const series = PLATFORMS.map((platform) => {
    const own = rows.filter((r) => r.platform_id === platform.id)
    // Split into segments so unavailable/null entries leave a gap instead of a fake ₹0 point.
    const segments = []
    let current = []
    own.forEach((r) => {
      if (hasPrice(r)) {
        current.push([x(new Date(r.recorded_at).getTime()), y(Number(r.price))])
      } else if (current.length) {
        segments.push(current)
        current = []
      }
    })
    if (current.length) segments.push(current)
    return { platform, segments }
  }).filter((s) => s.segments.length)

  const ticks = [pMin, (pMin + pMax) / 2, pMax]

  return (
    <div className="sc-history-chart mb-3">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Price history chart" className="w-100">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.left} x2={W - pad.right} y1={y(t)} y2={y(t)} stroke="#dfe6e1" />
            <text x={pad.left - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#52605a">
              ₹{t.toFixed(0)}
            </text>
          </g>
        ))}
        <text x={pad.left} y={H - 8} fontSize="11" fill="#52605a">
          {formatDate(new Date(tMin).toISOString()).split(',')[0]}
        </text>
        <text x={W - pad.right} y={H - 8} fontSize="11" fill="#52605a" textAnchor="end">
          {formatDate(new Date(tMax).toISOString()).split(',')[0]}
        </text>
        {series.map(({ platform, segments }) =>
          segments.map((seg, i) => (
            <g key={`${platform.id}-${i}`}>
              {seg.length > 1 && (
                <polyline fill="none" stroke={platform.color} strokeWidth="2" points={seg.map((p) => p.join(',')).join(' ')} />
              )}
              {seg.map((p, j) => (
                <circle key={j} cx={p[0]} cy={p[1]} r="3.5" fill={platform.color} />
              ))}
            </g>
          ))
        )}
      </svg>
      <div className="d-flex flex-wrap gap-3 small">
        {series.map(({ platform }) => (
          <span key={platform.id} className="d-inline-flex align-items-center gap-1">
            <span className="sc-history-dot" style={{ backgroundColor: platform.color }} />
            {platform.name}
          </span>
        ))}
      </div>
    </div>
  )
}

function PriceHistory({ productId }) {
  const [platformId, setPlatformId] = useState('')
  const [rows, setRows] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)

  // New product: go back to "All Platforms".
  useEffect(() => {
    setPlatformId('')
  }, [productId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    setRows(null)

    getProductHistory(productId, platformId)
      .then((data) => {
        if (cancelled) return
        setRows(Array.isArray(data && data.history) ? data.history : [])
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    // Ignore stale responses after product/filter change or unmount.
    return () => {
      cancelled = true
    }
  }, [productId, platformId, retry])

  // Oldest first from backend; show newest first in the table.
  const tableRows = rows ? [...rows].reverse() : []

  return (
    <section className="mt-4" aria-label="Price History">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h3 className="h5 mb-0">Price History</h3>
        <select
          className="form-select form-select-sm w-auto"
          aria-label="Filter by platform"
          value={platformId}
          onChange={(e) => setPlatformId(e.target.value)}
        >
          <option value="">All Platforms</option>
          {PLATFORMS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="sc-history-card p-3">
        {loading && <p className="text-muted mb-0">Loading price history...</p>}

        {!loading && error && (
          <p className="mb-0">
            <span className="text-danger">Unable to load price history.</span>{' '}
            <button type="button" className="btn btn-link btn-sm p-0 align-baseline" onClick={() => setRetry((n) => n + 1)}>
              Try again
            </button>
          </p>
        )}

        {!loading && !error && rows && rows.length === 0 && (
          <p className="text-muted mb-0">No price history available yet.</p>
        )}

        {!loading && !error && rows && rows.length > 0 && (
          <>
            <HistoryChart rows={rows} />
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>Platform</th>
                    <th>Price</th>
                    <th>Date</th>
                    <th>Availability</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row, i) => {
                    const platform = platformById(row.platform_id)
                    const ok = hasPrice(row)
                    return (
                      <tr key={`${row.platform_id}-${row.recorded_at}-${i}`}>
                        <td>{platform ? platform.name : `Platform ${row.platform_id}`}</td>
                        <td>{ok ? formatPrice(row.price) : <span className="text-muted">Unavailable</span>}</td>
                        <td className="text-nowrap">{formatDate(row.recorded_at) || '—'}</td>
                        <td>
                          <span className={`badge ${ok ? 'text-bg-success' : 'text-bg-secondary'}`}>
                            {ok ? 'Available' : 'Unavailable'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  )
}

export default PriceHistory
