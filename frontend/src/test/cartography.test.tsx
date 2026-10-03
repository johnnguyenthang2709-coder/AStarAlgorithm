import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { defaultLayers, parseContext, roadClass, roadName, selectStreetLabels, toggleLayer, type LabelCandidate } from '../road/cartography'
import { MapLayersControl } from '../road/MapLayersControl'

const candidate = (name: string, x = 150, y = 150, rank = 0, length = 80): LabelCandidate => ({ name, x, y, rank, length, lat: 10, lon: 106, angle: 0 })
describe('local cartography', () => {
  it('groups OSM highway values with the strongest class taking precedence', () => {
    expect(roadClass('secondary')).toBe('major')
    expect(roadClass('tertiary_link')).toBe('medium')
    expect(roadClass('residential')).toBe('local')
    expect(roadClass(['service', 'primary'])).toBe('major')
    expect(roadClass(null)).toBe('minor')
  })
  it('uses actual names without inventing missing street text', () => {
    expect(roadName(['Lý Thường Kiệt', 'Lý Thường Kiệt'])).toBe('Lý Thường Kiệt')
    expect(roadName(null)).toBeNull()
  })
  it('deduplicates a street and chooses its longest eligible segment', () => {
    const labels = selectStreetLabels([candidate('Street', 150, 150, 0, 50), candidate('street', 350, 150, 0, 100)], 600, 400)
    expect(labels).toHaveLength(1)
    expect(labels[0].x).toBe(350)
  })
  it('avoids collisions, map edges and route/endpoint reservations', () => {
    const labels = selectStreetLabels([candidate('Route', 150), candidate('Edge', 5), candidate('Clear', 350), candidate('Collision', 350, 152, 1)], 600, 400, [{ x: 150, y: 150, radius: 30 }])
    expect(labels.map(x => x.name)).toEqual(['Clear'])
  })
  it('rejects an invalid context response', () => {
    expect(() => parseContext({ type: 'FeatureCollection' })).toThrow('Invalid local map context')
    const context = { type: 'FeatureCollection', features: [], center: { lat: 10, lon: 106 }, counts: { buildings: 0, pois: 0 } }
    expect(parseContext(context)).toBe(context)
  })
  it('toggles one layer without changing algorithm/other layer choices', () => {
    expect(defaultLayers.arrows).toBe(false)
    expect(defaultLayers.nodes).toBe(false)
    expect(toggleLayer(defaultLayers, 'arrows')).toEqual({ ...defaultLayers, arrows: true })
  })
  it('only exposes building controls when polygons exist and reports a toggle', async () => {
    const toggle = vi.fn(), user = userEvent.setup()
    render(<MapLayersControl layers={defaultLayers} buildingsAvailable={false} onToggle={toggle} />)
    await user.click(screen.getByText('Map layers'))
    expect(screen.queryByRole('checkbox', { name: 'Buildings' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'One-way arrows' }))
    expect(toggle).toHaveBeenCalledWith('arrows')
  })
})
