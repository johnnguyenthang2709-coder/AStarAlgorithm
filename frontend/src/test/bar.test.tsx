import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BarPage } from '../robot/BarPage'
import { simulateBar } from '../api/bar'
import type { BarFrame, BarResponse } from '../types/bar'

vi.mock('../api/bar', () => ({ simulateBar: vi.fn() }))
const cell = (col: number) => ({ row: 0, col })
const frame = (event: BarFrame['event'], col: number, changes: BarFrame['changes'] = []): BarFrame => ({
  event, position: cell(col), changes, target: null, path: [], entry_path: [], anchor: null,
  phase: null, fallback: null, status: null, entry_length: null, retreat_length: null,
  retreat_ratio: null, invariant_verified: null,
})
const result: BarResponse = {
  scenario: 'open_route', map_kind: 'grid', radius: 1, rows: 1, cols: 3, start: cell(0), goal: cell(2),
  status: 'goal_reached', success: true, recoveries: [],
  frames: [frame('sense', 0, [{ cell: cell(0), state: 0 }, { cell: cell(1), state: 0 }]),
    { ...frame('plan', 0), target: cell(1), path: [cell(0), cell(1)] },
    frame('move', 1), frame('sense', 1, [{ cell: cell(2), state: 0 }]), frame('finish', 2)],
  metrics: { executed_distance: 2, turn_count: 0, astar_expanded_nodes: 4,
    replanning_count: 2, planning_time_ms: 0.5, gate_entry_length: null,
    gate_retreat_length: null, gate_retreat_ratio: null, gate_bound_verified: null,
    gate_entries: 0, gate_exits: 0, bar_evaluation_status: 'no_gate' },
}
beforeEach(() => vi.mocked(simulateBar).mockResolvedValue(result))

describe('BAR playback', () => {
  it('shows only observations available at the selected frame', async () => {
    const user = userEvent.setup()
    render(<BarPage />)
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(simulateBar).toHaveBeenCalledWith('irregular_u', 2))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 3: unknown/ })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /Row 1, column 2: free, frontier/ })).toHaveClass('frontier-cell')
    await user.click(screen.getByRole('checkbox', { name: 'Show frontiers' }))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 2: free/ })).not.toHaveClass('frontier-cell')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Playback speed' }), '4')
    expect(screen.getByRole('combobox', { name: 'Playback speed' })).toHaveValue('4')
    await user.click(screen.getByRole('button', { name: 'Step' }))
    await user.click(screen.getByRole('button', { name: 'Step' }))
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 3: free/ })).toBeInTheDocument()
    expect(screen.queryByText('Reached')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Step' }))
    expect(screen.getByText('Reached')).toBeInTheDocument()
  })

  it('sends selected scenario and radius', async () => {
    const user = userEvent.setup()
    render(<BarPage />)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Map' }), 'unreachable')
    await user.clear(screen.getByRole('spinbutton', { name: 'Sensor radius (cells)' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Sensor radius (cells)' }), '3')
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    expect(simulateBar).toHaveBeenCalledWith('unreachable', 3)
  })

  it('renders polygon-derived occupancy only after sensing and toggles inspection grid', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateBar).mockResolvedValueOnce({ ...result, scenario: 'irregular_u', map_kind: 'polygon_grid' })
    render(<BarPage />)
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(screen.getByRole('grid', { name: 'Discovered BAR grid' })).toHaveClass('seamless-cells'))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 3: unknown/ })).toBeInTheDocument()
    expect(screen.getByText(/polygon-to-grid adaptation/)).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Grid lines' }))
    expect(screen.getByRole('grid', { name: 'Discovered BAR grid' })).toHaveClass('grid-lines')
  })

  it('jumps to a recovery without revealing the final outcome early', async () => {
    const user = userEvent.setup()
    const recovery: BarResponse = {
      ...result, scenario: 'expedition_narrow', rows: 32, cols: 32,
      frames: [frame('sense', 0, [{ cell: cell(0), state: 0 }, { cell: cell(1), state: 0 }]),
        frame('move', 1),
        { ...frame('recover_start', 1), anchor: cell(0), entry_path: [cell(0), cell(1)], path: [cell(1), cell(0)], fallback: false },
        { ...frame('move', 0), phase: 'retreat' }, frame('finish', 0)],
    }
    vi.mocked(simulateBar).mockResolvedValueOnce(recovery)
    render(<BarPage />)
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await waitFor(() => expect(screen.getAllByRole('gridcell')).toHaveLength(32 * 32))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 3: unknown/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next recovery' }))
    expect(screen.getByText('A* computes the return')).toBeInTheDocument()
    expect(screen.getByText('Frame 3 / 5')).toBeInTheDocument()
    expect(screen.queryByText('Reached')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(screen.getByText('150%')).toBeInTheDocument()
  })
})
