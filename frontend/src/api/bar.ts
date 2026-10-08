import { request } from './client'
import type { BarResponse, BarScenario } from '../types/bar'

export const simulateBar = (scenario: BarScenario, radius: number) =>
  request<BarResponse>('/api/bar/simulate', { scenario, radius })
