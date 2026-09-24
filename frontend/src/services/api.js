/**
 * Central API service layer.
 *
 * Every function here matches docs/API_CONTRACT.md section 6 EXACTLY:
 *   getHealth()
 *   getProducts({ page, per_page, category })
 *   getProductById(id)
 *   searchProducts(query, limit)
 *   compareProduct(id)
 *
 * Components must never call fetch/axios directly and must never import
 * mockData.js directly — everything goes through this file.
 *
 * Switching between mock data and the real Flask backend is controlled
 * entirely by the VITE_USE_MOCK env variable.
 */

import * as mock from './mockData'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

/**
 * Standard error shape thrown by every function in this file.
 * Always carries a `code` (matches API_CONTRACT.md error codes) and a
 * human-readable `message`, so pages never need to parse raw responses.
 */
export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

function buildUrl(path, params = {}) {
  const url = new URL(`${API_BASE_URL}/api${path}`)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value)
    }
  })
  return url.toString()
}

async function request(path, params = {}) {
  let response
  try {
    response = await fetch(buildUrl(path, params))
  } catch (err) {
    throw new ApiError(
      'NETWORK_ERROR',
      'Unable to reach the server. Please check your connection and try again.'
    )
  }

  let data
  try {
    data = await response.json()
  } catch (err) {
    throw new ApiError('INTERNAL_SERVER_ERROR', 'Received an invalid response from the server.')
  }

  if (!response.ok) {
    const errorInfo = data && data.error ? data.error : {}
    throw new ApiError(
      errorInfo.code || 'INTERNAL_SERVER_ERROR',
      errorInfo.message || 'Something went wrong. Please try again later.'
    )
  }

  return data
}

/* ---------------------------------------------------------------- */
/* GET /api/health                                                   */
/* ---------------------------------------------------------------- */
export async function getHealth() {
  if (USE_MOCK) {
    return mock.mockGetHealth()
  }
  return request('/health')
}

/* ---------------------------------------------------------------- */
/* GET /api/products                                                 */
/* ---------------------------------------------------------------- */
export async function getProducts({ page = 1, per_page = 20, category } = {}) {
  if (USE_MOCK) {
    return mock.mockGetProducts({ page, per_page, category })
  }
  return request('/products', { page, per_page, category })
}

/* ---------------------------------------------------------------- */
/* GET /api/products/<id>                                            */
/* ---------------------------------------------------------------- */
export async function getProductById(id) {
  if (USE_MOCK) {
    return mock.mockGetProductById(id)
  }
  return request(`/products/${encodeURIComponent(id)}`)
}

/* ---------------------------------------------------------------- */
/* GET /api/products/search                                          */
/* ---------------------------------------------------------------- */
export async function searchProducts(query, limit = 20) {
  if (USE_MOCK) {
    return mock.mockSearchProducts(query, limit)
  }
  return request('/products/search', { q: query, limit })
}

/* ---------------------------------------------------------------- */
/* GET /api/products/<id>/compare                                    */
/* ---------------------------------------------------------------- */
export async function compareProduct(id) {
  if (USE_MOCK) {
    return mock.mockCompareProduct(id)
  }
  return request(`/products/${encodeURIComponent(id)}/compare`)
}