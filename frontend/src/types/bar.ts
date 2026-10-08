import type { GridCell } from './common'

export type BarScenario = 'alley_reachable' | 'alley_turn' | 'alley_shortcut' | 'wide_mouth_alley' | 'open_route' | 'unreachable' | 'expedition_narrow' | 'expedition_wide' | 'irregular_u' | 'irregular_bugtrap'
export type BarFrame = {
  event: 'sense' | 'plan' | 'move' | 'recover_start' | 'recover_end' | 'finish'
  position: GridCell
  changes: { cell: GridCell; state: 0 | 1 }[]
  target: GridCell | null
  path: GridCell[]
  entry_path: GridCell[]
  anchor: GridCell | null
  phase: 'explore' | 'retreat' | null
  fallback: boolean | null
  status: string | null
  entry_length: number | null
  retreat_length: number | null
  retreat_ratio: number | null
  invariant_verified: boolean | null
}
export type BarResponse = {
  scenario: BarScenario
  map_kind: 'grid' | 'polygon_grid'
  radius: number
  rows: number
  cols: number
  start: GridCell
  goal: GridCell
  status: string
  success: boolean
  frames: BarFrame[]
  recoveries: { anchor: GridCell; entry_length: number; retreat_length: number; retreat_ratio: number | null; fallback: boolean; invariant_verified: boolean }[]
  metrics: {
    executed_distance: number
    turn_count: number
    astar_expanded_nodes: number
    replanning_count: number
    planning_time_ms: number
    gate_entry_length: number | null
    gate_retreat_length: number | null
    gate_retreat_ratio: number | null
    gate_bound_verified: boolean | null
    gate_entries: number
    gate_exits: number
    bar_evaluation_status: 'no_gate' | 'no_entry' | 'entered_no_exit' | 'uncertified_exit' | 'certified' | 'bound_failed'
  }
}
