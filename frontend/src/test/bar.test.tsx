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
  scenario: 'open_route', radius: 1, rows: 1, cols: 3, start: cell(0), goal: cell(2),
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
    await waitFor(() => expect(simulateBar).toHaveBeenCalledWith('alley_reachable', 2))
    expect(screen.getByRole('gridcell', { name: /Row 1, column 3: unknown/ })).toBeInTheDocument()
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
})
