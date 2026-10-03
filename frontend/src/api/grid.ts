import { request } from './client'
import type { GridReplanRequest, GridSearchRequest, GridSearchResponse } from '../types/grid'
export const gridSearch = (body: GridSearchRequest) => request<GridSearchResponse>('/api/grid/search', body)
export const gridReplan = (body: GridReplanRequest) => request<GridSearchResponse>('/api/grid/replan', body)
