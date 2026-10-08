export type WorldPoint = { x: number; y: number }
export type SensedRegion = {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: number[][][] | number[][][][]
}
export type ContinuousFrame = {
  event: 'sense' | 'plan' | 'move' | 'recover_start' | 'recover_end' | 'branch' | 'finish'
  position: WorldPoint
  heading: number
  region?: SensedRegion
  obstacle_edges?: [WorldPoint, WorldPoint][]
  new_area?: number
  new_wall_fragments?: number
  observed_wall_fragments?: number
  target?: WorldPoint
  path?: WorldPoint[]
  entry_path?: WorldPoint[]
  anchor?: WorldPoint
  fallback?: boolean
  trigger?: 'exhausted_branch' | 'graph_blocked_target' | 'occluded_frontier_deferred'
  decision?: {
    reason: string
    eligible: number
    estimated_gain?: number | null
    estimated_travel?: number
    active_branch?: number
    parent_branch?: number | null
  }
  entry_length?: number
  retreat_length?: number
  retreat_ratio?: number
  invariant_verified?: boolean
  phase?: 'explore' | 'goal' | 'retreat'
  distance?: number
  status?: string
  graph_nodes?: number
  graph_edges?: number
  graph_points?: WorldPoint[]
  graph_links?: [number, number][]
  branch_id?: number
  parent_id?: number | null
}
export type ContinuousScenario = 'irregular_u' | 'irregular_bugtrap' | 'maze_showcase' | 'maze_hard' | 'maze_seeded' | 'lab_exploration' | 'lab_alley' | 'lab_complex' | 'lab_seeded' | 'indoor_apartment' | 'indoor_office' | 'indoor_challenge' | 'indoor_seeded'
export type IndoorOptions = { seed: number; indoor_layout: 'apartment' | 'office' | 'challenge' }
export type MazeOptions = {
  seed: number
  size: number
  corridor_width: number
  loop_rate: number
  dead_end_rate: number
  trap_count: number
  difficulty: 'easy' | 'normal' | 'hard'
  irregularity?: number
  start_cell?: [number, number] | null
  goal_cell?: [number, number] | null
}
export type ContinuousBarResponse = {
  scenario: ContinuousScenario
  mode: 'continuous'
  radius: number
  sensor_fov_degrees: 360
  robot_radius: 0
  bounds: [number, number, number, number]
  y_axis: 'up' | 'down'
  start: WorldPoint
  goal: WorldPoint
  status: string
  success: boolean
  frames: ContinuousFrame[]
  maze_config?: MazeOptions | null
  indoor_config?: IndoorOptions | null
  recoveries: {
    anchor: WorldPoint
    entry_length: number
    retreat_length: number
    retreat_ratio: number | null
    fallback: boolean
    trigger?: 'exhausted_branch' | 'graph_blocked_target' | 'occluded_frontier_deferred'
    invariant_verified: boolean
  }[]
  metrics: {
    executed_distance: number
    turn_count: number
    astar_expanded_nodes: number
    replanning_count: number
    planning_time_ms: number
    max_graph_nodes: number
    max_graph_edges: number
    observed_free_area?: number
    observed_branches?: number
    ranking_time_ms?: number
    observed_wall_fragments?: number
  }
}
