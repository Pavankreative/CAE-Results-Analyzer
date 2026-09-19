import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../api'

const ok = (body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), {
    status: 200, headers: { 'content-type': 'application/json' },
  }))

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('requests the simulation list and parses JSON', async () => {
    const fetchMock = vi.fn((..._args: unknown[]) => ok([{ id: 'brk-114' }]))
    vi.stubGlobal('fetch', fetchMock)
    const sims = await api.simulations()
    expect(fetchMock).toHaveBeenCalledWith('/api/simulations', expect.anything())
    expect(sims[0].id).toBe('brk-114')
  })

  it('passes the domain filter as a query parameter', async () => {
    const fetchMock = vi.fn((..._args: unknown[]) => ok([]))
    vi.stubGlobal('fetch', fetchMock)
    await api.simulations('CFD')
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/simulations?domain=CFD')
  })

  it('surfaces the backend detail message on an error status', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(
      JSON.stringify({ detail: "simulation 'ghost' not found" }),
      { status: 404, headers: { 'content-type': 'application/json' } },
    ))))
    await expect(api.simulation('ghost')).rejects.toThrow("simulation 'ghost' not found")
  })

  it('explains an unreachable backend instead of a raw network error', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('failed to fetch'))))
    await expect(api.health()).rejects.toBeInstanceOf(ApiError)
    await expect(api.health()).rejects.toThrow(/Cannot reach the backend/)
  })

  it('posts a comparison request with both simulation ids', async () => {
    const fetchMock = vi.fn((..._args: unknown[]) => ok({ same_mesh: true }))
    vi.stubGlobal('fetch', fetchMock)
    await api.compare('a', 'b')
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toMatchObject({ simulation_a: 'a', simulation_b: 'b' })
  })
})
