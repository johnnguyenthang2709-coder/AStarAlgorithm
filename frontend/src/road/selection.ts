import type { Coordinate } from '../types/common'
export type Selection = { start: Coordinate | null; goal: Coordinate | null }
export type PickMode = 'start' | 'goal' | null
export function selectPoint(selection: Selection, mode: PickMode, point: Coordinate): Selection {
  if (mode === 'start') return { ...selection, start: point }
  if (mode === 'goal') return { ...selection, goal: point }
  return selection
}
