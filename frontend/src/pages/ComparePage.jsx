import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import SearchBar from '../components/SearchBar'
import ProductGrid from '../components/ProductGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'
import { getProducts, searchProducts } from '../services/api'

function ComparePage() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSearching, setIsSearching] = useState(false)
  const [activeQuery, setActiveQuery] = useState('')
  const [category, setCategory] = useState('')
  const requestId = useRef(0) // ignore stale responses when requests overlap

  const loadProducts = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    setCategory('')
    try {
      const data = await getProducts({ page: 1, per_page: 50 })
      if (id !== requestId.current) return
      setProducts(Array.isArray(data.products) ? data.products : [])
    } catch (err) {
      if (id !== requestId.current) return
      setError(err)
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  const handleSearch = async (query) => {
    setIsSearching(true)
    setActiveQuery(query)
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    setCategory('')
    try {
      const data = await searchProducts(query, 50)
      if (id !== requestId.current) return
      setProducts(Array.isArray(data.products) ? data.products : [])
    } catch (err) {
      if (id !== requestId.current) return
      setError(err)
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }

  // Category chips come from the categories actually present in the response.
  const categories = useMemo(() => [...new Set(products.map((p) => p.category).filter(Boolean))].sort(), [products])
  const visible = category ? products.filter((p) => p.category === category) : products

  const handleClearSearch = () => {
    setIsSearching(false)
    setActiveQuery('')
    loadProducts()
  }

  return (
    <div>
      <section className="sc-hero py-4">
        <div className="container">
          <h1 className="h3">Compare Grocery Prices</h1>
          <p className="mb-0">Pick a product below to see its price on every platform, side by side.</p>
        </div>
      </section>

      <SearchBar onSearch={handleSearch} onClear={handleClearSearch} isSearching={isSearching} query={activeQuery} />

      <section className="container py-5">
        {loading && <LoadingSpinner label={isSearching ? 'Searching...' : 'Loading products...'} />}

        {!loading && error && (
          <ErrorMessage
            message={error.message}
            onRetry={isSearching ? () => handleSearch(activeQuery) : loadProducts}
          />
        )}

        {!loading && !error && products.length === 0 && (
          <EmptyState
            icon={isSearching ? '🔍' : '🛒'}
            title={isSearching ? 'No products found' : 'No products available'}
            message={
              isSearching
                ? `We couldn't find anything matching "${activeQuery}".`
                : 'Check back soon — products are being added.'
            }
          />
        )}

        {!loading && !error && products.length > 0 && (
          <>
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
              <p className="text-muted small mb-0" role="status">
                {isSearching
                  ? `${visible.length} result${visible.length === 1 ? '' : 's'} for "${activeQuery}"`
                  : `${visible.length} product${visible.length === 1 ? '' : 's'}`}
                {category ? ` in ${category}` : ''}
              </p>
              {categories.length > 1 && (
                <div className="d-flex flex-wrap gap-2" role="group" aria-label="Filter by category">
                  {['', ...categories].map((c) => (
                    <button
                      key={c || 'all'}
                      type="button"
                      className={`btn btn-sm ${category === c ? 'btn-forest' : 'btn-outline-forest'}`}
                      aria-pressed={category === c}
                      onClick={() => setCategory(c)}
                    >
                      {c || 'All'}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <ProductGrid products={visible} />
          </>
        )}
      </section>
    </div>
  )
}

export default ComparePage