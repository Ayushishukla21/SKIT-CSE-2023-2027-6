import { Link } from 'react-router-dom'

function ProductCard({ product }) {
  const initials = product.name.charAt(0).toUpperCase()

  return (
    <div className="sc-product-card p-3">
      <div className="sc-product-thumb mb-3">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="img-fluid" />
        ) : (
          <span>{initials}</span>
        )}
      </div>

      <span className="badge sc-category-badge mb-2">{product.category}</span>

      <h3 className="h6 mb-1">{product.name}</h3>
      <p className="text-muted small mb-2">
        {product.brand} &middot; {product.quantity}
        {product.unit}
      </p>

      <Link to={`/compare/${product.id}`} className="btn btn-outline-forest btn-sm w-100 mt-2">
        Compare Prices
      </Link>
    </div>
  )
}

export default ProductCard