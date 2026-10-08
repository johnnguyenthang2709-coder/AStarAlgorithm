export type WorldPoint = { x: number; y: number }
export type SensedRegion = {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: number[][][] | number[][][][]
}
export type ContinuousFrame = {
  event: 'sense' | 'plan' | 'move' | 'recover_start' | 'recover_end' | 'finish'
  position: WorldPoint
  heading: number
  region?: SensedRegion
  obstacle_edges?: [WorldPoint, WorldPoint][]
  new_area?: number
  target?: WorldPoint
  path?: WorldPoint[]
  entry_path?: WorldPoint[]
  anchor?: WorldPoint
  fallback?: boolean
  entry_length?: number
  retreat_length?: number
  retreat_ratio?: number
  invariant_verified?: boolean
  phase?: 'explore' | 'goal' | 'retreat'
  distance?: number
  status?: string
  graph_nodes?: number
  graph_edges?: number
}
export type ContinuousBarResponse = {
  scenario: 'irregular_u' | 'irregular_bugtrap'
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
  recoveries: {
    anchor: WorldPoint
    entry_length: number
    retreat_length: number
    retreat_ratio: number | null
    fallback: boolean
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
  }
}
