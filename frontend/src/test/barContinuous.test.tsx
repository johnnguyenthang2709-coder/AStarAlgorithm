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
    await waitFor(() => expect(simulateContinuousBar).toHaveBeenCalledWith('lab_exploration', 5, { debug_graph: false }))
    expect(screen.getByRole('img', { name: 'Discovered continuous robot map' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByText('Frame 2 / 4')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(screen.getByText('125%')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Full executed trail' }))
    await user.click(screen.getByRole('button', { name: 'Grid baseline' }))
    expect(screen.getByText('Four directions · unit cost')).toBeInTheDocument()
  })

  it('sends seeded maze parameters and graph debug only when requested', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateContinuousBar).mockResolvedValue({ ...result, frames: result.frames.map(frame =>
      frame.event === 'plan' ? { ...frame, graph_points: [start, end], graph_links: [[0, 1]] } : frame) })
    const view = render(<BarPage />)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Map' }), 'maze_seeded')
    await user.clear(screen.getByRole('spinbutton', { name: 'Seed' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Seed' }), '23')
    await user.click(screen.getByRole('checkbox', { name: /Visibility graph debug/ }))
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(simulateContinuousBar).toHaveBeenCalledWith('maze_seeded', 5,
      expect.objectContaining({ seed: 23, size: 5, corridor_width: 2.8, debug_graph: true })))
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(view.container.querySelectorAll('.continuous-graph-link')).toHaveLength(1)
  })

  it('exposes the seeded irregular labyrinth controls and preserves playback geometry', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateContinuousBar).mockResolvedValue(result)
    const view = render(<BarPage />)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Map' }), 'lab_seeded')
    await user.clear(screen.getByRole('spinbutton', { name: 'Irregularity' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Irregularity' }), '0.8')
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(simulateContinuousBar).toHaveBeenCalledWith('lab_seeded', 5,
      expect.objectContaining({ irregularity: 0.8, seed: 17, debug_graph: false })))
    expect(view.container.querySelector('.labyrinth-map-stage')).toBeInTheDocument()
    expect(view.container.querySelector('.continuous-free')?.getAttribute('d')).not.toContain('NaN')
    expect(view.container.querySelector('.continuous-obstacle')?.getAttribute('fill')).toBe('none')
    const scrubber = screen.getByRole('slider', { name: 'Playback frame' })
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(scrubber).toHaveValue('1')
    await user.click(screen.getByRole('button', { name: 'Restart' }))
    expect(scrubber).toHaveValue('0')
  })

  it('labels a graph-blocked target separately from branch exhaustion', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateContinuousBar).mockResolvedValue({ ...result, frames: result.frames.map(frame =>
      frame.event === 'plan' ? { ...frame, path: [], status: 'unreachable_target' } : frame) })
    render(<BarPage />)
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await screen.findByRole('img', { name: 'Discovered continuous robot map' })
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByText('Target unreachable on known graph')).toBeInTheDocument()
  })

  it('selects a seeded indoor layout and replays observed parent branches', async () => {
    const user = userEvent.setup()
    const indoorResult: ContinuousBarResponse = { ...result, scenario: 'indoor_seeded',
      indoor_config: { indoor_layout: 'challenge', seed: 211 },
      metrics: { ...result.metrics, observed_branches: 2, observed_free_area: 30 },
      frames: [result.frames[0],
        { event: 'branch', position: start, heading: 0, branch_id: 1, parent_id: 0, status: 'active', anchor: start },
        ...result.frames.slice(1)] }
    vi.mocked(simulateContinuousBar).mockResolvedValue(indoorResult)
    render(<BarPage />)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Map' }), 'indoor_seeded')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Floor plan' }), 'challenge')
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(simulateContinuousBar).toHaveBeenCalledWith('indoor_seeded', 5,
      expect.objectContaining({ indoor_layout: 'challenge', seed: 41, debug_graph: false })))
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByText('Entered observed branch 1')).toBeInTheDocument()
    expect(screen.getByText('Observed branch')).toBeInTheDocument()
    expect(buildContinuousPlayback(indoorResult)[1].branchId).toBe(1)
  })
})
