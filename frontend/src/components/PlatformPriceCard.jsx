function PlatformPriceCard({ entry, isBest }) {
  const cardClass = `sc-platform-card${isBest ? ' is-best' : ''}${!entry.available ? ' is-unavailable' : ''}`

  return (
    <div className={cardClass}>
      <div className="d-flex justify-content-between align-items-start mb-2">
        <h4 className="h6 mb-0">{entry.platform}</h4>
        {isBest && entry.available && <span className="sc-best-tag">Best Price</span>}
      </div>

      {entry.available ? (
        <p className="h5 mb-1" style={{ color: 'var(--sc-forest)' }}>
          &#8377;{entry.price.toFixed(2)}
        </p>
      ) : (
        <p className="h6 text-muted mb-1">Unavailable</p>
      )}

      {entry.offer && (
        <span className="sc-offer-tag d-inline-block mt-1">
          {entry.offer.title}
          {entry.offer.discount_amount != null ? ` (₹${entry.offer.discount_amount.toFixed(2)} off)` : ''}
        </span>
      )}
    </div>
  )
}

export default PlatformPriceCard