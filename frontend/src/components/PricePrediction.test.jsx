import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import PricePrediction, { classifyPredictionError } from './PricePrediction'
import { ApiError, getProductHistory, getProductPrediction } from '../services/api'

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api')
  return { ...actual, getProductHistory: vi.fn(), getProductPrediction: vi.fn() }
})

const product = { id: 1, name: 'Amul Taaza Milk' }
const prices = [
  { platform_id: 1, platform: 'Blinkit', price: 60, available: true },
  { platform_id: 2, platform: 'Zepto', price: 58, available: true },
  { platform_id: 3, platform: 'Instamart', price: null, available: false }
]
const history = {
  history: [
    { platform_id: 2, price: 57, available: true, recorded_at: '2026-10-10T10:00:00Z' },
    { platform_id: 2, price: 58, available: true, recorded_at: '2026-10-14T10:00:00Z' }
  ]
}
const forecast = {
  current_price: 58,
  available_periods: [7, 30],
  predictions: [
    { date: '2026-10-29', days_ahead: 7, predicted_price: 61.25 },
    { date: '2026-11-22', days_ahead: 30, predicted_price: 64.5 }
  ]
}

describe('PricePrediction', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    getProductHistory.mockResolvedValue(history)
  })

  it('shows a loading state first', () => {
    getProductPrediction.mockReturnValue(new Promise(() => {}))
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    expect(screen.getByRole('status')).toHaveTextContent(/loading price prediction/i)
  })

  it('shows PREDICTION_UNAVAILABLE without any predicted price', async () => {
    getProductPrediction.mockRejectedValue(
      new ApiError('PREDICTION_UNAVAILABLE', 'Price prediction is not available yet for this product', 404)
    )
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    expect(await screen.findByText(/prediction not available yet/i)).toBeInTheDocument()
    expect(screen.queryByText(/^predicted price/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument()
  })

  it('treats PRODUCT_NOT_FOUND as an error, not as "unavailable"', async () => {
    getProductPrediction.mockRejectedValue(new ApiError('PRODUCT_NOT_FOUND', 'Product not found', 404))
    render(<PricePrediction product={product} prices={prices} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Product not found')
    expect(screen.queryByText(/prediction not available yet/i)).not.toBeInTheDocument()
  })

  it('shows an error with retry that re-requests', async () => {
    getProductPrediction.mockRejectedValueOnce(new ApiError('NETWORK_ERROR', 'Unable to reach the server.'))
    getProductPrediction.mockRejectedValueOnce(new ApiError('PREDICTION_UNAVAILABLE', 'nope', 404))
    render(<PricePrediction product={product} prices={prices} />)
    await userEvent.click(await screen.findByRole('button', { name: /try again/i }))
    expect(await screen.findByText(/prediction not available yet/i)).toBeInTheDocument()
    expect(getProductPrediction).toHaveBeenCalledTimes(2)
  })

  it('shows an empty state when the API returns no usable predictions', async () => {
    getProductPrediction.mockResolvedValue({ predictions: [{ date: '2026-10-29', predicted_price: null }] })
    render(<PricePrediction product={product} prices={prices} />)
    expect(await screen.findByText(/returned no usable forecast prices/i)).toBeInTheDocument()
  })

  it('requests the best available platform by default and renders only API values', async () => {
    getProductPrediction.mockResolvedValue(forecast)
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    expect(await screen.findByText('₹61.25')).toBeInTheDocument()
    expect(getProductPrediction).toHaveBeenCalledWith(1, 2, undefined)
    expect(getProductHistory).toHaveBeenCalledWith(1, 2)
    expect(screen.getByText(/\+₹3\.25 \(\+5\.6%\)/)).toBeInTheDocument()
    expect(screen.queryByText('₹64.50')).not.toBeInTheDocument()
  })

  it('sends the selected forecast period as days and keeps the period selector', async () => {
    getProductPrediction.mockResolvedValue(forecast)
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    await screen.findByText('₹61.25')
    await userEvent.selectOptions(screen.getByLabelText('Prediction period'), '30')
    await waitFor(() => expect(getProductPrediction).toHaveBeenLastCalledWith(1, 2, '30'))
    expect(await screen.findByText('₹64.50')).toBeInTheDocument()
  })

  it('changing platform makes exactly one new request and resets the period', async () => {
    getProductPrediction.mockResolvedValue(forecast)
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    await screen.findByText('₹61.25')
    await userEvent.selectOptions(screen.getByLabelText('Prediction period'), '30')
    await screen.findByText('₹64.50')
    getProductPrediction.mockClear()
    await userEvent.selectOptions(screen.getByLabelText('Prediction platform'), '1')
    await waitFor(() => expect(getProductPrediction).toHaveBeenCalledWith(1, 1, undefined))
    expect(getProductPrediction).toHaveBeenCalledTimes(1)
  })

  it('still shows the forecast if history fails', async () => {
    getProductHistory.mockRejectedValue(new ApiError('DATABASE_ERROR', 'db'))
    getProductPrediction.mockResolvedValue(forecast)
    render(<PricePrediction product={product} prices={prices} bestPlatform="Zepto" />)
    expect(await screen.findByText('₹61.25')).toBeInTheDocument()
    expect(screen.getByText(/history could not be loaded/i)).toBeInTheDocument()
  })
})

describe('classifyPredictionError', () => {
  it('maps codes', () => {
    expect(classifyPredictionError({ code: 'PREDICTION_UNAVAILABLE', status: 404 })).toBe('unavailable')
    expect(classifyPredictionError({ code: 'PRODUCT_NOT_FOUND', status: 404 })).toBe('notfound')
    expect(classifyPredictionError({ code: 'DATABASE_ERROR', status: 503 })).toBe('error')
    expect(classifyPredictionError({ status: 404 })).toBe('error')
  })
})
