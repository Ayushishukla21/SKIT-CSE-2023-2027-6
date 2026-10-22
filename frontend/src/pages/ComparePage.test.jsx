import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import ComparePage from './ComparePage'
import { getProducts, searchProducts } from '../services/api'

vi.mock('../services/api', () => ({ getProducts: vi.fn(), searchProducts: vi.fn() }))

const P = (id, name, category) => ({ id, name, brand: 'B', category, quantity: 1, unit: 'L', image_url: null })
const renderPage = () => render(<MemoryRouter><ComparePage /></MemoryRouter>)

describe('ComparePage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('lists products and filters by category using response data', async () => {
    getProducts.mockResolvedValue({ products: [P(1, 'Milk', 'Dairy'), P(2, 'Atta', 'Staples')] })
    renderPage()
    expect(await screen.findByText('Milk')).toBeInTheDocument()
    expect(screen.getByText('2 products')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Staples' }))
    expect(screen.queryByText('Milk')).not.toBeInTheDocument()
    expect(screen.getByText('1 product in Staples')).toBeInTheDocument()
  })

  it('shows result count for a search and the empty state for count 0', async () => {
    getProducts.mockResolvedValue({ products: [P(1, 'Milk', 'Dairy')] })
    searchProducts.mockResolvedValueOnce({ query: 'milk', products: [P(1, 'Milk', 'Dairy')], count: 1 })
    renderPage()
    await screen.findByText('Milk')
    await userEvent.type(screen.getByLabelText('Search products'), 'milk')
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('1 result for "milk"')).toBeInTheDocument()

    searchProducts.mockResolvedValueOnce({ query: 'zzz', products: [], count: 0 })
    await userEvent.clear(screen.getByLabelText('Search products'))
    await userEvent.type(screen.getByLabelText('Search products'), 'zzz')
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('No products found')).toBeInTheDocument()
  })

  it('shows an error with retry when the API fails', async () => {
    getProducts.mockRejectedValueOnce({ code: 'DATABASE_ERROR', message: 'Database error. Please try again later' })
    getProducts.mockResolvedValueOnce({ products: [P(1, 'Milk', 'Dairy')] })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Milk')).toBeInTheDocument()
  })
})
