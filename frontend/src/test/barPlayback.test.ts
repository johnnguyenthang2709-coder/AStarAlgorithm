import { describe, expect, it } from 'vitest'
import { buildBarPlayback, observedFrontiers } from '../robot/barPlayback'
import type { BarFrame, BarResponse } from '../types/bar'

function event(kind: BarFrame['event'], col: number, changes: BarFrame['changes'] = []): BarFrame {
  return { event: kind, position: { row: 0, col }, changes, target: null, path: [],
    entry_path: [], anchor: null, phase: null, fallback: null, status: null,
    entry_length: null, retreat_length: null, retreat_ratio: null, invariant_verified: null }
}

describe('large-map playback snapshots', () => {
  it('supports direct seeking without changing earlier observed knowledge', () => {
    const frames = Array.from({ length: 700 }, (_, index) => event('sense', 0,
      index < 40 ? [{ cell: { row: 0, col: index }, state: 0 }] : []))
    const result = { rows: 40, cols: 40, frames, start: { row: 0, col: 0 } } as BarResponse
    const timeline = buildBarPlayback(result)
    expect(timeline).toHaveLength(700)
    expect(timeline[0].known[39]).toBe(-1)
    expect(timeline[39].known[39]).toBe(0)
    expect(timeline[699].observed).toBe(40)
    expect(timeline[0].known[39]).toBe(-1)
    expect(observedFrontiers(timeline[0].known, 40, 40).has(0)).toBe(true)
    expect(observedFrontiers(timeline[699].known, 40, 40).has(39)).toBe(true)
  })
})
