import type { Algorithm, GridCell, SearchMetrics, TraceEvent } from './common'
export type GridSearchRequest = { grid: number[][]; start: GridCell; goal: GridCell; movement: 4 | 8; algorithm: Algorithm; trace: boolean }
export type GridReplanRequest = { grid: number[][]; current: GridCell; goal: GridCell; new_obstacles: GridCell[]; movement: 4 | 8; algorithm: Algorithm; trace: boolean }
export type GridSearchResponse = { found: boolean; cost: number | null; path: GridCell[]; metrics: SearchMetrics; trace: TraceEvent<GridCell>[] }
