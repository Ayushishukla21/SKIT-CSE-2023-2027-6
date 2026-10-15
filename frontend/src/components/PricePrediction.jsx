import { useEffect, useMemo, useState } from 'react'
import { getProductHistory, getProductPrediction } from '../services/api'

/*
 * Price Prediction section.
 *
 * Expected (proposed) response of GET /api/products/<id>/prediction
 *   ?platform_id=<id>&days=<n>   (platform_id and days are optional):
 * {
 *   "product_id": 1, "platform_id": 1, "currency": "INR",
 *   "current_price": 52.0,
 *   "generated_at": "2026-10-15T10:00:00Z",
 *   "available_periods": [7, 30],
 *   "predictions": [
 *     { "date": "2026-10-22", "days_ahead": 7, "predicted_price": 54.5 }
 *   ]
 * }
 * Nothing here is generated client-side: no response => "not available".
 */

const PLATFORMS = [
  { id: 1, name: 'Blinkit' },
  { id: 2, name: 'Zepto' },
  { id: 3, name: 'Instamart' },
  { id: 4, name: 'Flipkart Minutes' }
]

const HIST_COLOR = '#2d6a4f'
const PRED_COLOR = '#e76f51'

const money = (v) => `₹${Number(v).toFixed(2)}`
const shortDate = (t) => new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

function PredictionChart({ history, predictions, currentPrice }) {
  const W = 640
  const H = 240
  const pad = { top: 16, right: 16, bottom: 30, left: 52 }

  const hist = history
    .filter((r) => r.available !== false && r.price != null)
    .map((r) => ({ t: new Date(r.recorded_at).getTime(), p: Number(r.price) }))
    .sort((a, b) => a.t - b.t)
  const pred = predictions
    .map((r) => ({ t: new Date(r.date).getTime(), p: Number(r.predicted_price) }))
    .filter((r) => !Number.isNaN(r.t) && !Number.isNaN(r.p))
    .sort((a, b) => a.t - b.t)

  const all = [...hist, ...pred]
  if (all.length < 2) return <p className="text-muted mb-0">Not enough data to draw a chart.</p>

  const tMin = Math.min(...all.map((d) => d.t))
  const tMax = Math.max(...all.map((d) => d.t))
  let pMin = Math.min(...all.map((d) => d.p))
  let pMax = Math.max(...all.map((d) => d.p))
  if (pMin === pMax) {
    pMin -= 1
    pMax += 1
  }
  const x = (t) => pad.left + (tMax === tMin ? 0.5 : (t - tMin) / (tMax - tMin)) * (W - pad.left - pad.right)
  const y = (p) => pad.top + (1 - (p - pMin) / (pMax - pMin)) * (H - pad.top - pad.bottom)
  const pts = (arr) => arr.map((d) => `${x(d.t)},${y(d.p)}`).join(' ')

  // Join the predicted line to the last historical point so the gap isn't misleading.
  const lastHist = hist.length ? hist[hist.length - 1] : null
  const predLine = lastHist && pred.length ? [lastHist, ...pred] : pred
  const ticks = [pMin, (pMin + pMax) / 2, pMax]
  const divider = lastHist && pred.length ? x(lastHist.t) : null

  return (
    <div className="mb-3">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Historical and predicted price chart" className="w-100">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.left} x2={W - pad.right} y1={y(t)} y2={y(t)} stroke="#dfe6e1" />
            <text x={pad.left - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#52605a">
              ₹{t.toFixed(0)}
            </text>
          </g>
        ))}
        {divider !== null && (
          <line x1={divider} x2={divider} y1={pad.top} y2={H - pad.bottom} stroke="#9aa5a0" strokeDasharray="2 3" />
        )}
        <text x={pad.left} y={H - 8} fontSize="11" fill="#52605a">{shortDate(tMin)}</text>
        <text x={W - pad.right} y={H - 8} fontSize="11" fill="#52605a" textAnchor="end">{shortDate(tMax)}</text>
        {hist.length > 1 && <polyline fill="none" stroke={HIST_COLOR} strokeWidth="2" points={pts(hist)} />}
        {hist.map((d, i) => <circle key={i} cx={x(d.t)} cy={y(d.p)} r="3" fill={HIST_COLOR} />)}
        {predLine.length > 1 && (
          <polyline fill="none" stroke={PRED_COLOR} strokeWidth="2" strokeDasharray="6 4" points={pts(predLine)} />
        )}
        {pred.map((d, i) => <circle key={i} cx={x(d.t)} cy={y(d.p)} r="3.5" fill={PRED_COLOR} />)}
      </svg>
      <div className="d-flex flex-wrap gap-3 small">
        <span className="d-inline-flex align-items-center gap-1">
          <span className="sc-legend-line" style={{ borderColor: HIST_COLOR }} /> Historical Price
        </span>
        {pred.length > 0 && (
          <span className="d-inline-flex align-items-center gap-1">
            <span className="sc-legend-line dashed" style={{ borderColor: PRED_COLOR }} /> Predicted Price
          </span>
        )}
      </div>
    </div>
  )
}

function PricePrediction({ product }) {
  const [platformId, setPlatformId] = useState(1)
  const [days, setDays] = useState('')
  const [history, setHistory] = useState([])
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | unavailable | error
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    setDays('')
  }, [product.id, platformId])

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    setData(null)

    // History failure must not block the prediction card: treat it as empty.
    const histP = getProductHistory(product.id, platformId).then(
      (d) => (Array.isArray(d && d.history) ? d.history : []),
      () => []
    )
    const predP = getProductPrediction(product.id, platformId, days)

    Promise.all([histP, predP.then((d) => ({ d }), (e) => ({ e }))]).then(([h, r]) => {
      if (cancelled) return
      setHistory(h)
      if (r.e) {
        const unavailable = r.e.status === 404 || r.e.code === 'MOCK_UNSUPPORTED' || r.e.code === 'NOT_FOUND'
        setStatus(unavailable ? 'unavailable' : 'error')
        return
      }
      const preds = r.d && Array.isArray(r.d.predictions) ? r.d.predictions : []
      if (!preds.length) {
        setStatus('unavailable')
        return
      }
      setData(r.d)
      setStatus('ready')
    })
    return () => {
      cancelled = true
    }
  }, [product.id, platformId, days, retry])

  const periods = useMemo(() => {
    if (!data) return []
    const list = Array.isArray(data.available_periods) && data.available_periods.length
      ? data.available_periods
      : data.predictions.map((p) => p.days_ahead)
    return [...new Set(list.map(Number).filter((n) => n > 0))].sort((a, b) => a - b)
  }, [data])

  const activePeriod = days !== '' ? Number(days) : periods.length ? periods[0] : null
  const shown = data
    ? data.predictions.filter((p) => activePeriod == null || p.days_ahead == null || p.days_ahead <= activePeriod)
    : []
  const target = shown.length ? shown[shown.length - 1] : null
  const current = data && data.current_price != null ? Number(data.current_price) : null
  const change = target && current != null ? Number(target.predicted_price) - current : null
  const pct = change != null && current ? (change / current) * 100 : null
  const sign = (n) => (n > 0 ? '+' : '')
  const trendClass = change == null || change === 0 ? '' : change > 0 ? 'text-danger' : 'text-success'

  return (
    <section className="mt-4" aria-label="Price Prediction">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h3 className="h5 mb-0">Price Prediction</h3>
        <div className="d-flex flex-wrap gap-2">
          <select
            className="form-select form-select-sm w-auto"
            aria-label="Prediction platform"
            value={platformId}
            onChange={(e) => setPlatformId(Number(e.target.value))}
          >
            {PLATFORMS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {periods.length > 1 && (
            <select
              className="form-select form-select-sm w-auto"
              aria-label="Prediction period"
              value={activePeriod}
              onChange={(e) => setDays(e.target.value)}
            >
              {periods.map((n) => (
                <option key={n} value={n}>{n} days</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="sc-prediction-card p-3">
        {status === 'loading' && <p className="text-muted mb-0" role="status">Loading price prediction...</p>}

        {status === 'unavailable' && (
          <p className="text-muted mb-0">
            Prediction not available yet for this product. It will appear here once the prediction service is ready.
          </p>
        )}

        {status === 'error' && (
          <p className="mb-0">
            <span className="text-danger">Unable to load price prediction.</span>{' '}
            <button type="button" className="btn btn-link btn-sm p-0 align-baseline" onClick={() => setRetry((n) => n + 1)}>
              Try again
            </button>
          </p>
        )}

        {status === 'ready' && data && (
          <>
            <div className="row g-3 mb-3">
              <div className="col-6 col-md-3">
                <div className="small text-muted">Product</div>
                <div className="fw-semibold">{product.name}</div>
                <div className="small text-muted">
                  {(PLATFORMS.find((p) => p.id === platformId) || {}).name}
                </div>
              </div>
              <div className="col-6 col-md-3">
                <div className="small text-muted">Current price</div>
                <div className="fw-semibold">{current != null ? money(current) : '—'}</div>
              </div>
              <div className="col-6 col-md-3">
                <div className="small text-muted">
                  Predicted price{activePeriod ? ` (${activePeriod} days)` : ''}
                </div>
                <div className="fw-semibold">{target ? money(target.predicted_price) : '—'}</div>
              </div>
              <div className="col-6 col-md-3">
                <div className="small text-muted">Expected change</div>
                <div className={`fw-semibold ${trendClass}`}>
                  {change != null ? `${sign(change)}${money(change).replace('₹-', '-₹')}` : '—'}
                  {pct != null && ` (${sign(pct)}${pct.toFixed(1)}%)`}
                </div>
              </div>
            </div>
            <PredictionChart history={history} predictions={shown} currentPrice={current} />
            <p className="small text-muted mb-0">
              This is an estimate, not a guaranteed price. Actual prices may differ.
            </p>
          </>
        )}
      </div>
    </section>
  )
}

export default PricePrediction
