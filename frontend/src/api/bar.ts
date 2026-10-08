import { request } from './client'
import type { BarResponse, BarScenario } from '../types/bar'
import type { ContinuousBarResponse } from '../types/barContinuous'

export const simulateBar = (scenario: BarScenario, radius: number) =>
  request<BarResponse>('/api/bar/simulate', { scenario, radius })

export const simulateContinuousBar = (scenario: ContinuousBarResponse['scenario'], radius: number) =>
  request<ContinuousBarResponse>('/api/bar/continuous', { scenario, radius })
