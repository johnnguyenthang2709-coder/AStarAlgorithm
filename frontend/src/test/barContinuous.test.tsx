import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BarPage } from '../robot/BarPage'
import { buildContinuousPlayback, interpolatedPose } from '../robot/barContinuousPlayback'
import { simulateContinuousBar } from '../api/bar'
import type { ContinuousBarResponse } from '../types/barContinuous'

vi.mock('../api/bar', () => ({ simulateBar: vi.fn(), simulateContinuousBar: vi.fn() }))

const start = { x: 1, y: 1 }
const end = { x: 4, y: 5 }
const result: ContinuousBarResponse = {
  scenario: 'irregular_u', mode: 'continuous', radius: 6, sensor_fov_degrees: 360,
  robot_radius: 0, bounds: [0, 0, 10, 10], y_axis: 'up', start, goal: end,
  status: 'goal_reached', success: true, recoveries: [],
  metrics: { executed_distance: 5, turn_count: 0, astar_expanded_nodes: 2,
    replanning_count: 1, planning_time_ms: 0.1, max_graph_nodes: 2, max_graph_edges: 1 },
  frames: [
    { event: 'sense', position: start, heading: 0, new_area: 10,
      region: { type: 'Polygon', coordinates: [[[0, 0], [6, 0], [6, 6], [0, 6], [0, 0]]] },
      obstacle_edges: [[{ x: 6, y: 0 }, { x: 6, y: 6 }]] },
    { event: 'plan', position: start, heading: 0, target: end, path: [start, end] },
    { event: 'move', position: end, heading: Math.atan2(4, 3), phase: 'goal', distance: 5 },
    { event: 'finish', position: end, heading: Math.atan2(4, 3), status: 'goal_reached' },
  ],
}

describe('continuous playback', () => {
  it('interpolates arbitrary-angle motion and accumulates observations only after sense frames', () => {
    expect(interpolatedPose(result.frames, 1.5).position).toEqual({ x: 2.5, y: 3 })
    const states = buildContinuousPlayback(result)
    expect(states[0].regions).toHaveLength(1)
    expect(states[0].trail).toHaveLength(1)
    expect(states[1].path).toEqual([start, end])
    expect(states[2].trail).toEqual([start, end])
    expect(states[2].distance).toBe(5)
  })

  it('renders the continuous map and supports step, scrub, zoom and grid baseline switch', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateContinuousBar).mockResolvedValue(result)
    render(<BarPage />)
    expect(screen.getByText('Continuous 2D')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(simulateContinuousBar).toHaveBeenCalledWith('irregular_u', 6))
    expect(screen.getByRole('img', { name: 'Discovered continuous robot map' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByText('Frame 2 / 4')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(screen.getByText('125%')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Grid baseline' }))
    expect(screen.getByText('Four directions · unit cost')).toBeInTheDocument()
  })
})
