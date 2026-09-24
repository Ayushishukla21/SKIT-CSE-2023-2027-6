/**
 * Mock data layer.
 *
 * Values here are copied EXACTLY from docs/DATA_SCHEMA.md (frozen seed
 * data) and shaped EXACTLY like the real API responses described in
 * docs/API_CONTRACT.md, so switching VITE_USE_MOCK=false swaps to the
 * real backend with zero changes anywhere else in the app.
 *
 * Do NOT import this file directly from components — always go through
 * src/services/api.js.
 */

import { ApiError } from './api'

const MOCK_DELAY_MS = 400

function delay(ms = MOCK_DELAY_MS) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isPositiveIntegerString(value) {
  return /^[1-9]\d*$/.test(String(value).trim())
}

/* ---------------------------------------------------------------- */
/* Seed data (from docs/DATA_SCHEMA.md)                              */
/* ---------------------------------------------------------------- */

export const PRODUCTS = [
  { id: 1, name: 'Amul Taaza Milk', brand: 'Amul', category: 'Dairy', quantity: 1, unit: 'L', image_url: null },
  { id: 2, name: 'Aashirvaad Atta', brand: 'Aashirvaad', category: 'Staples', quantity: 5, unit: 'kg', image_url: null },
  { id: 3, name: 'Tata Salt', brand: 'Tata', category: 'Staples', quantity: 1, unit: 'kg', image_url: null },
  { id: 4, name: 'Tata Tea', brand: 'Tata', category: 'Beverages', quantity: 250, unit: 'g', image_url: null },
  { id: 5, name: 'Maggi 2-Minute Noodles', brand: 'Maggi', category: 'Packaged Food', quantity: 70, unit: 'g', image_url: null },
  { id: 6, name: 'Parle-G Biscuits', brand: 'Parle', category: 'Snacks', quantity: 250, unit: 'g', image_url: null }
]

const LAST_UPDATED = '2026-09-01T10:00:00Z'

// Pre-sorted per the ordering rule in API_CONTRACT.md 3.5:
// available first (cheapest -> most expensive, ties by smaller platform_id),
// then unavailable platforms last (by platform_id).
const COMPARE_DATA = {
  1: {
    prices: [
      { platform_id: 2, platform: 'Zepto', price: 65.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: 67.0, currency: 'INR', available: true, offer: null },
      { platform_id: 1, platform: 'Blinkit', price: 68.0, currency: 'INR', available: true, offer: null },
      { platform_id: 3, platform: 'Instamart', price: 70.0, currency: 'INR', available: true, offer: null }
    ],
    summary: { lowest_price: 65.0, highest_price: 70.0, potential_saving: 5.0, best_platform: 'Zepto' }
  },
  2: {
    prices: [
      { platform_id: 2, platform: 'Zepto', price: 259.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: 262.0, currency: 'INR', available: true, offer: null },
      {
        platform_id: 1,
        platform: 'Blinkit',
        price: 265.0,
        currency: 'INR',
        available: true,
        offer: { title: 'Flat ₹10 off', description: null, discount_amount: 10.0 }
      },
      { platform_id: 3, platform: 'Instamart', price: 272.0, currency: 'INR', available: true, offer: null }
    ],
    summary: { lowest_price: 259.0, highest_price: 272.0, potential_saving: 13.0, best_platform: 'Zepto' }
  },
  3: {
    prices: [
      { platform_id: 2, platform: 'Zepto', price: 27.0, currency: 'INR', available: true, offer: null },
      { platform_id: 1, platform: 'Blinkit', price: 28.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: 28.0, currency: 'INR', available: true, offer: null },
      { platform_id: 3, platform: 'Instamart', price: 29.0, currency: 'INR', available: true, offer: null }
    ],
    summary: { lowest_price: 27.0, highest_price: 29.0, potential_saving: 2.0, best_platform: 'Zepto' }
  },
  4: {
    prices: [
      { platform_id: 2, platform: 'Zepto', price: 142.0, currency: 'INR', available: true, offer: null },
      { platform_id: 1, platform: 'Blinkit', price: 145.0, currency: 'INR', available: true, offer: null },
      { platform_id: 3, platform: 'Instamart', price: 148.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: null, currency: 'INR', available: false, offer: null }
    ],
    summary: { lowest_price: 142.0, highest_price: 148.0, potential_saving: 6.0, best_platform: 'Zepto' }
  },
  5: {
    // Three-way tie at ₹14 between Blinkit(1), Zepto(2), Flipkart Minutes(4).
    // Tie-break = smaller platform_id, so Blinkit is the best platform here.
    prices: [
      { platform_id: 1, platform: 'Blinkit', price: 14.0, currency: 'INR', available: true, offer: null },
      { platform_id: 2, platform: 'Zepto', price: 14.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: 14.0, currency: 'INR', available: true, offer: null },
      { platform_id: 3, platform: 'Instamart', price: 15.0, currency: 'INR', available: true, offer: null }
    ],
    summary: { lowest_price: 14.0, highest_price: 15.0, potential_saving: 1.0, best_platform: 'Blinkit' }
  },
  6: {
    // Tie at ₹24 between Zepto(2) and Instamart(3) -> Zepto wins (smaller platform_id).
    prices: [
      { platform_id: 2, platform: 'Zepto', price: 24.0, currency: 'INR', available: true, offer: null },
      {
        platform_id: 3,
        platform: 'Instamart',
        price: 24.0,
        currency: 'INR',
        available: true,
        offer: { title: 'Save ₹2', description: null, discount_amount: 2.0 }
      },
      { platform_id: 1, platform: 'Blinkit', price: 25.0, currency: 'INR', available: true, offer: null },
      { platform_id: 4, platform: 'Flipkart Minutes', price: 26.0, currency: 'INR', available: true, offer: null }
    ],
    summary: { lowest_price: 24.0, highest_price: 26.0, potential_saving: 2.0, best_platform: 'Zepto' }
  }
}

/* ---------------------------------------------------------------- */
/* Mock endpoint implementations                                     */
/* ---------------------------------------------------------------- */

export async function mockGetHealth() {
  await delay(150)
  return { status: 'ok', service: 'smartcart-api', database: 'connected', contract_version: '1.0' }
}

export async function mockGetProducts({ page = 1, per_page = 20, category } = {}) {
  await delay()

  const pageNum = Number(page)
  const perPageNum = Number(per_page)

  if (!Number.isInteger(pageNum) || pageNum < 1) {
    throw new ApiError('INVALID_PARAMETER', 'page must be a positive integer.')
  }
  if (!Number.isInteger(perPageNum) || perPageNum < 1 || perPageNum > 50) {
    throw new ApiError('INVALID_PARAMETER', 'per_page must be between 1 and 50.')
  }

  let filtered = PRODUCTS
  if (category) {
    filtered = filtered.filter((p) => p.category === category)
  }

  const total = filtered.length
  const total_pages = Math.max(1, Math.ceil(total / perPageNum))
  const start = (pageNum - 1) * perPageNum
  const products = filtered.slice(start, start + perPageNum)

  return {
    products,
    pagination: { page: pageNum, per_page: perPageNum, total, total_pages }
  }
}

export async function mockGetProductById(id) {
  await delay()

  if (!isPositiveIntegerString(id)) {
    throw new ApiError('INVALID_PRODUCT_ID', 'Product ID must be a positive integer.')
  }

  const product = PRODUCTS.find((p) => p.id === Number(id))
  if (!product) {
    throw new ApiError('PRODUCT_NOT_FOUND', 'Product not found.')
  }

  return { product }
}

export async function mockSearchProducts(query, limit = 20) {
  await delay()

  const trimmed = (query || '').trim()
  if (!trimmed) {
    throw new ApiError('EMPTY_SEARCH_QUERY', 'Search query must not be empty.')
  }
  if (trimmed.length > 100) {
    throw new ApiError('INVALID_PARAMETER', 'Search query is too long.')
  }

  const limitNum = Number(limit)
  if (!Number.isInteger(limitNum) || limitNum < 1 || limitNum > 50) {
    throw new ApiError('INVALID_PARAMETER', 'limit must be between 1 and 50.')
  }

  const q = trimmed.toLowerCase()
  const matches = PRODUCTS.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      p.brand.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q)
  ).slice(0, limitNum)

  return { query: trimmed, products: matches, count: matches.length }
}

export async function mockCompareProduct(id) {
  await delay()

  if (!isPositiveIntegerString(id)) {
    throw new ApiError('INVALID_PRODUCT_ID', 'Product ID must be a positive integer.')
  }

  const product = PRODUCTS.find((p) => p.id === Number(id))
  if (!product) {
    throw new ApiError('PRODUCT_NOT_FOUND', 'Product not found.')
  }

  const compare = COMPARE_DATA[product.id] || { prices: [], summary: null }

  return {
    product,
    prices: compare.prices,
    summary:
      compare.summary || {
        lowest_price: null,
        highest_price: null,
        potential_saving: null,
        best_platform: null
      },
    meta: { data_source: 'demo', last_updated: compare.prices.length ? LAST_UPDATED : null }
  }
}