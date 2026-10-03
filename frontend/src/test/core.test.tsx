import { describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { request, ApiError } from '../api/client'
import { roadSearch } from '../api/road'
import { distance, score } from '../utils/format'
import { useTracePlayback } from '../hooks/useTracePlayback'
import { editScenario, initialScenario, sameCell } from '../robot/scenario'
import { selectPoint } from '../road/selection'
import { applyTraceState } from '../utils/traceState'

describe('API and presentation', () => {
  it('serializes the road search contract and reads a response', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ found: false, route: null, metrics: {}, trace: [], start: {}, goal: {} }) })
    vi.stubGlobal('fetch', fetcher)
    const body = { start: { lat: 10.77, lon: 106.66 }, goal: { lat: 10.78, lon: 106.67 }, algorithm: 'astar' as const, trace: true }
    expect((await roadSearch(body)).found).toBe(false)
    expect(fetcher).toHaveBeenCalledWith('http://127.0.0.1:8000/api/road/search', expect.objectContaining({ method: 'POST', body: JSON.stringify(body) }))
    vi.unstubAllGlobals()
  })
  it('distinguishes validation, road graph, network and server errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ detail: [{ msg: 'Invalid grid' }] }) }).mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'road graph unavailable' }) }).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: 'internal' }) }))
    await expect(request('/x')).rejects.toMatchObject({ kind: 'validation', message: 'Invalid grid' } satisfies Partial<ApiError>)
    await expect(request('/x')).rejects.toMatchObject({ kind: 'road_unavailable' })
    await expect(request('/x')).rejects.toMatchObject({ kind: 'network' })
    await expect(request('/x')).rejects.toMatchObject({ kind: 'server', message: 'Backend request failed (500).' })
    vi.unstubAllGlobals()
  })
  it('formats exact backend metrics only at presentation', () => {
    expect(distance(999.6)).toBe('1,000 m')
    expect(distance(3925.093)).toBe('3.93 km')
    expect(score(3.5)).toBe('3.50')
  })
})

describe('interaction state', () => {
  it('replaces selected road endpoints independently', () => {
    const a = { lat: 10, lon: 106 }, b = { lat: 11, lon: 107 }
    expect(selectPoint({ start: a, goal: null }, 'goal', b)).toEqual({ start: a, goal: b })
    expect(selectPoint({ start: a, goal: b }, 'start', b)).toEqual({ start: b, goal: b })
  })
  it('edits a grid without blocking endpoints and makes a new immutable grid for replan', () => {
    const original = initialScenario(), obstacle = { row: 10, col: 3 }
    const changed = editScenario(original, obstacle, 'obstacle')
    expect(changed.grid[10][3]).toBe(1)
    expect(original.grid[10][3]).toBe(0)
    expect(editScenario(changed, original.start, 'obstacle')).toBe(changed)
    expect(editScenario(changed, obstacle, 'erase').grid[10][3]).toBe(0)
    expect(sameCell(original.start, original.goal)).toBe(false)
  })
  it('replays, steps and restarts a trace', () => {
    vi.useFakeTimers()
    const events = Array.from({ length: 30 }, (_, i) => i)
    const { result } = renderHook(() => useTracePlayback(events))
    act(() => result.current.step())
    expect(result.current.index).toBe(1)
    act(() => { result.current.setSpeed(4); result.current.play() })
    act(() => vi.advanceTimersByTime(80))
    expect(result.current.index).toBe(21)
    act(() => result.current.restart())
    expect(result.current.index).toBe(0)
    expect(result.current.playing).toBe(false)
    vi.useRealTimers()
  })
  it('clears the selected event when a new trace arrives', () => {
    const first = [1, 2], second = [3]
    const { result, rerender } = renderHook(({ events }) => useTracePlayback(events), { initialProps: { events: first } })
    act(() => result.current.step())
    expect(result.current.current).toBe(1)
    rerender({ events: second })
    expect(result.current.index).toBe(0)
    expect(result.current.current).toBeNull()
  })
  it('moves a reopened state from expanded back to frontier', () => {
    const frontier = new Set<string>(), expanded = new Set<string>()
    const event = (type: 'DISCOVER' | 'EXPAND' | 'CLOSE' | 'UPDATE') => ({ type, state: 1, parent: null, g: 1, h: 2, f: 3 })
    applyTraceState(frontier, expanded, event('DISCOVER'), '1')
    applyTraceState(frontier, expanded, event('EXPAND'), '1')
    applyTraceState(frontier, expanded, event('CLOSE'), '1')
    expect(expanded.has('1')).toBe(true)
    applyTraceState(frontier, expanded, event('UPDATE'), '1')
    expect(frontier.has('1')).toBe(true)
    expect(expanded.has('1')).toBe(false)
  })
})
