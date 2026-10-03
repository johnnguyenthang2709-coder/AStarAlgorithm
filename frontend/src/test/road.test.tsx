import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RoadPage } from '../road/RoadPage'
import { roadCompare, roadNodes, roadSearch, roadSnap } from '../api/road'
import type { RoadSearchResponse } from '../types/road'

vi.mock('../road/RoadMap', () => ({ RoadMap: () => <div data-testid="road-map" /> }))
vi.mock('../api/road', () => ({ roadCompare: vi.fn(), roadNodes: vi.fn(), roadSearch: vi.fn(), roadSnap: vi.fn() }))

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
const metrics = { expanded_nodes: 2, unique_expanded_states: 2, generated_nodes: 3, unique_discovered_states: 3, relaxed_edges: 2, examined_edges: 4 }
const response = (cost: number): RoadSearchResponse => ({
  found: true, route: { cost_m: cost, node_path: [0, 1], edge_path: [{ from_node: 0, to_node: 1, length_m: cost, osm_key: '0', osmid: 1, name: '' }], geometry: [{ lat: 10, lon: 106 }, { lat: 11, lon: 107 }] },
  metrics, trace: [],
  start: { requested: { lat: 10, lon: 106 }, snapped: { lat: 10, lon: 106, node_id: 0, osm_id: 1, snap_distance_m: 0 } },
  goal: { requested: { lat: 11, lon: 107 }, snapped: { lat: 11, lon: 107, node_id: 1, osm_id: 2, snap_distance_m: 0 } },
})

describe('road request state', () => {
  it('ignores a route response after the goal changes', async () => {
    const user = userEvent.setup()
    const pending = deferred<RoadSearchResponse>()
    vi.mocked(roadSnap).mockImplementation(async point => ({ ...point, node_id: 0, osm_id: 1, snap_distance_m: 0 }))
    vi.mocked(roadNodes).mockResolvedValue([])
    vi.mocked(roadCompare).mockResolvedValue({} as never)
    vi.mocked(roadSearch).mockReturnValueOnce(pending.promise).mockResolvedValueOnce(response(2000))
    render(<RoadPage health={{ status: 'ok', road_graph_loaded: true, road_nodes: 2, road_edges: 1 }} healthError={null} />)
    await user.type(screen.getByRole('spinbutton', { name: 'Start latitude' }), '10')
    await user.type(screen.getByRole('spinbutton', { name: 'Start longitude' }), '106')
    await user.click(screen.getByRole('button', { name: 'Set start coordinates' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Destination latitude' }), '11')
    await user.type(screen.getByRole('spinbutton', { name: 'Destination longitude' }), '107')
    await user.click(screen.getByRole('button', { name: 'Set destination coordinates' }))
    await user.click(screen.getByRole('button', { name: 'Find route' }))
    expect(roadSearch).toHaveBeenCalledTimes(1)
    await user.clear(screen.getByRole('spinbutton', { name: 'Destination latitude' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Destination latitude' }), '12')
    await user.click(screen.getByRole('button', { name: 'Set destination coordinates' }))
    pending.resolve(response(1000))
    await waitFor(() => expect(screen.getByText('Awaiting route')).toBeInTheDocument())
    expect(screen.queryByText('1.00 km')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Find route' }))
    expect(await screen.findByText('2.00 km')).toBeInTheDocument()
  })
  it('clears route and inspector on reset', async () => {
    const user = userEvent.setup()
    vi.mocked(roadSnap).mockImplementation(async point => ({ ...point, node_id: 0, osm_id: 1, snap_distance_m: 0 }))
    vi.mocked(roadSearch).mockResolvedValue(response(2000))
    render(<RoadPage health={{ status: 'ok', road_graph_loaded: true, road_nodes: 2, road_edges: 1 }} healthError={null} />)
    await user.type(screen.getByRole('spinbutton', { name: 'Start latitude' }), '10')
    await user.type(screen.getByRole('spinbutton', { name: 'Start longitude' }), '106')
    await user.click(screen.getByRole('button', { name: 'Set start coordinates' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Destination latitude' }), '11')
    await user.type(screen.getByRole('spinbutton', { name: 'Destination longitude' }), '107')
    await user.click(screen.getByRole('button', { name: 'Set destination coordinates' }))
    await user.click(screen.getByRole('button', { name: 'Find route' }))
    expect(await screen.findByText('2.00 km')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reset points' }))
    expect(screen.getByText('Awaiting route')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Find route' })).toBeDisabled()
  })
})
