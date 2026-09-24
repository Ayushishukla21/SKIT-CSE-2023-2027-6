import { useState } from 'react'

function SearchBar({ onSearch, onClear, isSearching, query }) {
  const [value, setValue] = useState(query || '')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) return
    onSearch(trimmed)
  }

  const handleClear = () => {
    setValue('')
    if (onClear) onClear()
  }

  return (
    <div className="sc-search-wrap">
      <div className="container">
        <form className="sc-search-card d-flex align-items-center gap-2" onSubmit={handleSubmit}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="#52605A" strokeWidth="1.8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="#52605A" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            className="sc-search-input form-control"
            placeholder="Search for milk, atta, tea, biscuits..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            maxLength={100}
            aria-label="Search products"
          />
          {isSearching && (
            <button type="button" className="btn btn-outline-forest btn-sm" onClick={handleClear}>
              Clear
            </button>
          )}
          <button type="submit" className="btn btn-forest btn-sm px-3" disabled={!value.trim()}>
            Search
          </button>
        </form>
      </div>
    </div>
  )
}

export default SearchBar