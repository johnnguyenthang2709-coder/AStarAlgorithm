import { request } from './client'
import type { RoadGeometry } from '../road/cartography'
import { parseContext } from '../road/cartography'
import type { Coordinate } from '../types/common'
import type { Health, RoadCompareResponse, RoadNode, RoadSearchRequest, RoadSearchResponse, RoadSnap } from '../types/road'
export const healthCheck = () => request<Health>('/api/health')
export const roadSnap = (point: Coordinate) => request<RoadSnap>('/api/road/snap', point)
export const roadNodes = () => request<RoadNode[]>('/api/road/nodes')
export const roadGeometry = () => request<RoadGeometry>('/api/road/geometry')
export const roadContext = async () => parseContext(await request<unknown>('/api/road/context'))
export const roadSearch = (body: RoadSearchRequest) => request<RoadSearchResponse>('/api/road/search', body)
export const roadCompare = (start: Coordinate, goal: Coordinate) => request<RoadCompareResponse>('/api/road/compare', { start, goal, trace: false })
