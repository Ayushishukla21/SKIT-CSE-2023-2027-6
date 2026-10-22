import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getProductPrediction, getProductHistory, ApiError } from './api'

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })

describe('api.js prediction/history requests', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })
  afterEach(() => vi.restoreAllMocks())

  it('builds the prediction URL with platform_id and days', async () => {
    fetch.mockReturnValue(json({ predictions: [] }))
    await getProductPrediction(5, 2, 30)
    const url = new URL(fetch.mock.calls[0][0])
    expect(url.pathname).toBe('/api/products/5/prediction')
    expect(url.searchParams.get('platform_id')).toBe('2')
    expect(url.searchParams.get('days')).toBe('30')
  })

  it('omits days when not provided', async () => {
    fetch.mockReturnValue(json({ predictions: [] }))
    await getProductPrediction(5, 2)
    expect(new URL(fetch.mock.calls[0][0]).searchParams.has('days')).toBe(false)
  })

  it('turns the backend 404 PREDICTION_UNAVAILABLE body into an ApiError with that code', async () => {
    fetch.mockReturnValue(json({ error: { code: 'PREDICTION_UNAVAILABLE', message: 'not yet' } }, 404))
    await expect(getProductPrediction(1)).rejects.toMatchObject({ code: 'PREDICTION_UNAVAILABLE', status: 404, message: 'not yet' })
  })

  it('maps network failure to NETWORK_ERROR', async () => {
    fetch.mockRejectedValue(new TypeError('fail'))
    await expect(getProductHistory(1)).rejects.toBeInstanceOf(ApiError)
    await expect(getProductHistory(1)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })
})
