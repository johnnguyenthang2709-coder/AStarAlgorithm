export type Algorithm = 'astar' | 'dijkstra'
export type Coordinate = { lat: number; lon: number }
export type GridCell = { row: number; col: number }
export type SearchMetrics = {
  expanded_nodes: number
  unique_expanded_states: number
  generated_nodes: number
  unique_discovered_states: number
  relaxed_edges: number
  examined_edges: number
}
export type TraceEvent<T> = {
  type: 'DISCOVER' | 'EXPAND' | 'UPDATE' | 'CLOSE' | 'GOAL_FOUND'
  state: T
  parent: T | null
  g: number
  h: number
  f: number
}
