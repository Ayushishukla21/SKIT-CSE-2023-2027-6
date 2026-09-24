import { useEffect, useState, useCallback } from 'react'
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

  const loadProducts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getProducts({ page: 1, per_page: 50 })
      setProducts(data.products)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  const handleSearch = async (query) => {
    setIsSearching(true)
    setActiveQuery(query)
    setLoading(true)
    setError(null)
    try {
      const data = await searchProducts(query, 50)
      setProducts(data.products)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

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

        {!loading && !error && products.length > 0 && <ProductGrid products={products} />}
      </section>
    </div>
  )
}

export default ComparePage