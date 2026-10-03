import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { RoadMap } from '../road/RoadMap'
import type { RoadSearchResponse, RoadSnap } from '../types/road'

vi.mock('leaflet', () => ({ default: {
  control: { scale: () => ({ addTo: () => ({ remove: () => {} }) }) },
  divIcon: () => ({}),
  marker: () => ({ addTo: () => ({ bindPopup: () => {}, remove: () => {} }) }),
} }))
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Pane: () => null, TileLayer: () => null,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  CircleMarker: ({ center, children }: { center: number[]; children: ReactNode }) => <div data-testid="endpoint" data-center={JSON.stringify(center)}>{children}</div>,
  Polyline: ({ positions }: { positions: number[][] }) => <div data-testid="line" data-positions={JSON.stringify(positions)} />,
  useMap: () => ({ fitBounds: () => {} }), useMapEvents: () => {},
}))
vi.mock('../road/CartographyLayer', () => ({ CartographyLayer: () => null }))
vi.mock('../road/SearchLayer', () => ({ SearchLayer: () => null }))
vi.mock('../road/MapLayersControl', () => ({ MapLayersControl: () => null }))
vi.mock('../api/road', () => ({ roadGeometry: async () => null, roadContext: async () => null }))

it('places route markers at snapped road positions and retains a subtle request connector', () => {
  const start: RoadSnap = { lat: 10, lon: 106.0005, node_id: null, osm_id: null, from_node: 0, to_node: 1, fraction: .25, snap_distance_m: 11 }
  const goal: RoadSnap = { ...start, lon: 106.0015, fraction: .75, snap_distance_m: 0 }
  const result = { route: { geometry: [start, { lat: 10.001, lon: 106.001 }, goal] } } as RoadSearchResponse
  render(<RoadMap selection={{ start: { lat: 10.0001, lon: start.lon }, goal }} pickMode={null} onPick={() => {}} startSnap={start} goalSnap={goal} result={result} events={[]} index={0} nodes={[]} />)
  expect(screen.getAllByTestId('endpoint').map(node => JSON.parse(node.dataset.center!))).toEqual([[start.lat,start.lon],[goal.lat,goal.lon]])
  const lines = screen.getAllByTestId('line').map(node => JSON.parse(node.dataset.positions!))
  expect(lines[0]).toEqual([[start.lat,start.lon],[10.001,106.001],[goal.lat,goal.lon]])
  expect(lines[2]).toEqual([[10.0001,start.lon],[start.lat,start.lon]])
})
