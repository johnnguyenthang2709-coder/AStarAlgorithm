import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RobotPage } from '../robot/RobotPage'
import { gridReplan, gridSearch } from '../api/grid'
import type { GridSearchResponse } from '../types/grid'

vi.mock('../api/grid', () => ({ gridSearch: vi.fn(), gridReplan: vi.fn() }))
const response: GridSearchResponse = { found: true, cost: 2, path: [{ row: 10, col: 2 }, { row: 10, col: 3 }, { row: 10, col: 4 }], metrics: { expanded_nodes: 3, unique_expanded_states: 3, generated_nodes: 5, unique_discovered_states: 5, relaxed_edges: 4, examined_edges: 7 }, trace: [{ type: 'DISCOVER', state: { row: 10, col: 2 }, parent: null, g: 0, h: 2, f: 2 }] }
beforeEach(() => { vi.mocked(gridSearch).mockResolvedValue(response as never); vi.mocked(gridReplan).mockResolvedValue(response as never) })

describe('Robot Lab integration state', () => {
  it('sends selected algorithm and movement, then repeats A* for a new obstacle', async () => {
    const user = userEvent.setup()
    render(<RobotPage />)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Algorithm' }), 'dijkstra')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Movement' }), '4')
    await user.click(screen.getByRole('button', { name: 'Run search' }))
    await waitFor(() => expect(gridSearch).toHaveBeenCalledWith(expect.objectContaining({ algorithm: 'dijkstra', movement: 4, trace: true })))
    await user.click(screen.getByRole('gridcell', { name: /Row 11, column 6:/ }))
    await waitFor(() => expect(gridReplan).toHaveBeenCalledWith(expect.objectContaining({ current: { row: 10, col: 2 }, new_obstacles: [{ row: 10, col: 5 }], algorithm: 'astar' })))
    expect(screen.getByText(/Replans/).parentElement).toHaveTextContent('1')
  })
  it('renders a network failure without raw objects', async () => {
    vi.mocked(gridSearch).mockRejectedValueOnce(new Error('internal'))
    render(<RobotPage />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Run search' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('An unexpected error occurred.')
  })
  it('keeps only one grid cell in the tab order and supports arrow keys', async () => {
    const user = userEvent.setup()
    render(<RobotPage />)
    const cells = screen.getAllByRole('gridcell')
    expect(cells.filter(cell => cell.tabIndex === 0)).toHaveLength(1)
    const start = screen.getByRole('gridcell', { name: /Row 11, column 3:/ })
    start.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('gridcell', { name: /Row 11, column 4:/ })).toHaveFocus()
  })
  it('ignores a pending search after reset', async () => {
    let resolve!: (value: typeof response) => void
    vi.mocked(gridSearch).mockReturnValueOnce(new Promise(done => { resolve = done }))
    const user = userEvent.setup()
    render(<RobotPage />)
    await user.click(screen.getByRole('button', { name: 'Run search' }))
    await user.click(screen.getByRole('button', { name: 'Reset scenario' }))
    resolve(response)
    await waitFor(() => expect(screen.getByText('Awaiting search')).toBeInTheDocument())
    expect(screen.queryByText('Grid path cost')).not.toBeInTheDocument()
  })
})
