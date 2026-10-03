import type { Algorithm, Coordinate, SearchMetrics, TraceEvent } from './common'
export type Health = { status: 'ok' | 'degraded'; road_graph_loaded: boolean; road_nodes: number; road_edges: number }
export type RoadSnap = Coordinate & { node_id: number | null; osm_id: number | null; from_node?: number; to_node?: number; fraction?: number; snap_distance_m: number }
export type RoadNode = Coordinate & { node_id: number }
export type LocationMatch = { requested: Coordinate; snapped: RoadSnap }
export type RoadEdge = { from_node: number; to_node: number; length_m: number; osm_key: string; osmid: number | number[] | string | null; name: string }
export type RoadRoute = { cost_m: number; node_path: number[]; edge_path: RoadEdge[]; geometry: Coordinate[] }
export type RoadResult = { found: boolean; route: RoadRoute | null; metrics: SearchMetrics; trace: TraceEvent<number>[]; trace_nodes?: RoadNode[] }
export type RoadSearchResponse = RoadResult & { start: LocationMatch; goal: LocationMatch }
export type RoadCompareResponse = { start: LocationMatch; goal: LocationMatch; same_optimal_cost: boolean; cost_difference_m: number | null; astar: RoadResult; dijkstra: RoadResult }
export type RoadSearchRequest = { start: Coordinate; goal: Coordinate; algorithm: Algorithm; trace: boolean }
