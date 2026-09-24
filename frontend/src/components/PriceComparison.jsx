import PlatformPriceCard from './PlatformPriceCard'
import StatCard from './StatCard'
import DemoBadge from './DemoBadge'
import EmptyState from './EmptyState'

function formatDate(isoString) {
  if (!isoString) return null
  const date = new Date(isoString)
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatPrice(value) {
  return value == null ? '—' : `₹${value.toFixed(2)}`
}

function PriceComparison({ product, prices, summary, meta }) {
  return (
    <div>
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
        <div>
          <span className="badge sc-category-badge mb-2">{product.category}</span>
          <h2 className="h4 mb-1">
            {product.name} {product.quantity}
            {product.unit}
          </h2>
          <p className="text-muted mb-0">{product.brand}</p>
        </div>

        <div className="text-end">
          {meta.data_source === 'demo' && <DemoBadge />}
          {meta.last_updated && (
            <p className="small text-muted mt-2 mb-0">Updated {formatDate(meta.last_updated)}</p>
          )}
        </div>
      </div>

      {/* Summary — values come straight from the backend, never recalculated here */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <StatCard label="Lowest Price" value={formatPrice(summary.lowest_price)} icon="⬇️" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="Highest Price" value={formatPrice(summary.highest_price)} icon="⬆️" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="You Save" value={formatPrice(summary.potential_saving)} icon="💰" accent="gold" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="Best Platform" value={summary.best_platform || '—'} icon="🏆" accent="gold" />
        </div>
      </div>

      {prices.length === 0 ? (
        <EmptyState
          icon="🛒"
          title="No pricing data yet"
          message="None of the platforms currently list this product."
        />
      ) : (
        <div className="row g-3">
          {prices.map((entry) => (
            <div className="col-6 col-md-3" key={entry.platform_id}>
              <PlatformPriceCard entry={entry} isBest={entry.available && entry.platform === summary.best_platform} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default PriceComparison