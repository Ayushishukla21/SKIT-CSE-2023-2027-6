import PlatformPriceCard from './PlatformPriceCard'
import StatCard from './StatCard'
import DemoBadge from './DemoBadge'
import EmptyState from './EmptyState'

// Fixed platform seed from docs/DATA_SCHEMA.md section 2 (platforms table).
// Used only to keep all four platform slots visible in the UI even if the
// backend response for this product is missing an entry for one of them —
// this is a display concern only, it never invents a price or a summary
// value that the backend didn't provide.
const KNOWN_PLATFORMS = [
  { id: 1, name: 'Blinkit' },
  { id: 2, name: 'Zepto' },
  { id: 3, name: 'Instamart' },
  { id: 4, name: 'Flipkart Minutes' }
]

function buildPlatformSlots(prices) {
  const byPlatformId = new Map((prices || []).map((entry) => [entry.platform_id, entry]))

  return KNOWN_PLATFORMS.map((platform) => {
    const entry = byPlatformId.get(platform.id)
    if (entry) return entry

    // Platform wasn't in the API response at all — render it as a
    // distinct "no data" slot rather than silently hiding it.
    return {
      platform_id: platform.id,
      platform: platform.name,
      price: null,
      currency: 'INR',
      available: false,
      offer: null,
      noData: true
    }
  })
}
function formatDate(isoString) {
  if (!isoString) return null

  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return null

  const day = String(date.getDate()).padStart(2, '0')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const month = months[date.getMonth()]
  const year = date.getFullYear()

  let hours = date.getHours()
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const period = hours >= 12 ? 'PM' : 'AM'
  hours = hours % 12
  if (hours === 0) hours = 12
  const hoursStr = String(hours).padStart(2, '0')

  return `${day} ${month} ${year}, ${hoursStr}:${minutes} ${period}`
}

function formatPrice(value) {
  return value == null ? '—' : `₹${value.toFixed(2)}`
}

function PriceComparison({ product, prices, summary, meta }) {
  const hasPrices = Array.isArray(prices)
  const platformSlots = hasPrices ? buildPlatformSlots(prices) : []
  const availableCount = platformSlots.filter((entry) => entry.available).length

  // Defensive default only — never invents values, just avoids a crash if
  // the API response is missing the summary object entirely.
  const safeSummary = summary || {
    lowest_price: null,
    highest_price: null,
    potential_saving: null,
    best_platform: null
  }

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
          {hasPrices && (
            <p className="small text-muted mb-0 mt-1">
              Available on {availableCount} of {KNOWN_PLATFORMS.length} platforms
            </p>
          )}
        </div>

        <div className="text-end">
          {meta && meta.data_source === 'demo' && <DemoBadge />}
          {meta && meta.last_updated && (
          <p className="small text-muted mt-2 mb-0">Last updated: {formatDate(meta.last_updated)}</p>
          )}
        </div>
      </div>

      {/* Summary — values come straight from the backend, never recalculated here */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <StatCard label="Lowest Price" value={formatPrice(safeSummary.lowest_price)} icon="⬇️" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="Highest Price" value={formatPrice(safeSummary.highest_price)} icon="⬆️" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="You Save" value={formatPrice(safeSummary.potential_saving)} icon="💰" accent="gold" />
        </div>
        <div className="col-6 col-md-3">
          <StatCard label="Best Platform" value={safeSummary.best_platform || '—'} icon="🏆" accent="gold" />
        </div>
      </div>

      {!hasPrices ? (
        <EmptyState
          icon="🛒"
          title="No pricing data yet"
          message="None of the platforms currently list this product."
        />
      ) : (
        <div className="row g-3">
          {platformSlots.map((entry) => (
            <div className="col-6 col-md-3" key={entry.platform_id}>
              <PlatformPriceCard entry={entry} isBest={entry.available && entry.platform === safeSummary.best_platform} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default PriceComparison