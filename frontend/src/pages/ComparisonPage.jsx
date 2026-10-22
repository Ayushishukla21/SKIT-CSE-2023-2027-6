import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'
import PriceComparison from '../components/PriceComparison'
import { compareProduct } from '../services/api'

const NOT_FOUND_CODES = ['PRODUCT_NOT_FOUND', 'INVALID_PRODUCT_ID']

function ComparisonPage() {
  const { productId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await compareProduct(productId)
      setData(result)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [productId])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="container py-4">
      <Link to="/compare" className="d-inline-block mb-3 small">
        &larr; Back to all products
      </Link>

      {loading && <LoadingSpinner label="Loading comparison..." />}

      {!loading && error && NOT_FOUND_CODES.includes(error.code) && (
        <EmptyState
          icon="❓"
          title="Product not found"
          message="This product doesn't exist or may have been removed."
          actionLabel="Browse products"
          actionTo="/compare"
        />
      )}

      {!loading && error && !NOT_FOUND_CODES.includes(error.code) && (
        <ErrorMessage message={error.message} onRetry={load} />
      )}

      {!loading && !error && data && (
        <PriceComparison product={data.product} prices={data.prices} summary={data.summary} meta={data.meta} />
      )}
    </div>
  )
}

export default ComparisonPage