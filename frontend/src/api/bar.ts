import { request } from './client'
import type { BarResponse, BarScenario } from '../types/bar'
import type { ContinuousBarResponse, ContinuousScenario, IndoorOptions, MazeOptions } from '../types/barContinuous'

export const simulateBar = (scenario: BarScenario, radius: number) =>
  request<BarResponse>('/api/bar/simulate', { scenario, radius })

export const simulateContinuousBar = (scenario: ContinuousScenario, radius: number,
  options?: (Partial<MazeOptions> & Partial<IndoorOptions> & { debug_graph?: boolean; debug_exploration?: boolean })) =>
  request<ContinuousBarResponse>('/api/bar/continuous', { scenario, radius, ...options })
