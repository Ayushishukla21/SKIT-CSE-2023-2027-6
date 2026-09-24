import { useEffect, useState, useCallback } from 'react'
import HeroSection from '../components/HeroSection'
import SearchBar from '../components/SearchBar'
import ProductGrid from '../components/ProductGrid'
import FeatureCard from '../components/FeatureCard'
import HowItWorks from '../components/HowItWorks'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'
import { getProducts, searchProducts } from '../services/api'

const FEATURES = [
  { icon: '⚡', title: 'Instant Comparison', description: 'One click shows the price on every platform, side by side.' },
  { icon: '🏷️', title: 'Real Listed Prices', description: 'Prices shown are final selling prices — offers already applied.' },
  { icon: '🎯', title: 'No Guesswork', description: 'We tell you the cheapest platform and exactly how much you save.' }
]

function HomePage() {
  const [products, setProducts] = useState([])
  const [pagination, setPagination] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSearching, setIsSearching] = useState(false)
  const [activeQuery, setActiveQuery] = useState('')

  const loadProducts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getProducts({ page: 1, per_page: 20 })
      setProducts(data.products)
      setPagination(data.pagination)
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
      const data = await searchProducts(query, 20)
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
      <HeroSection />
      <SearchBar onSearch={handleSearch} onClear={handleClearSearch} isSearching={isSearching} query={activeQuery} />

      <section className="container py-5" id="products">
        <div className="d-flex justify-content-between align-items-end flex-wrap gap-2 mb-4">
          <div>
            <h2 className="h4 mb-1">{isSearching ? `Results for "${activeQuery}"` : 'Browse Products'}</h2>
            {!isSearching && pagination && (
              <p className="text-muted small mb-0">{pagination.total} products tracked across 4 platforms</p>
            )}
          </div>
        </div>

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
                ? `We couldn't find anything matching "${activeQuery}". Try a different search term.`
                : 'Check back soon — products are being added.'
            }
          />
        )}

        {!loading && !error && products.length > 0 && <ProductGrid products={products} />}
      </section>

      <section className="container pb-5">
        <div className="row g-3">
          {FEATURES.map((feature) => (
            <div className="col-md-4" key={feature.title}>
              <FeatureCard {...feature} />
            </div>
          ))}
        </div>
      </section>

      <HowItWorks />
    </div>
  )
}

export default HomePage