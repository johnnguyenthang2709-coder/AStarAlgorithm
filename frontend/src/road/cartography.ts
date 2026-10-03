import type { Feature, FeatureCollection, LineString, Geometry } from 'geojson'

export type RoadProperties = { from: number; to: number; length_m: number; osmid: number | number[] | null; name: string | string[] | null; highway?: string | string[] | null; oneway?: boolean | null }
export type RoadFeature = Feature<LineString, RoadProperties>
export type RoadGeometry = FeatureCollection<LineString, RoadProperties>
export type ContextProperties = { osm_id: string; building?: string; category?: string; name?: string | null }
export type MapContext = FeatureCollection<Geometry, ContextProperties> & { center: { lat: number; lon: number }; counts: { buildings: number; pois: number } }
export type Layers = { streets: boolean; buildings: boolean; landmarks: boolean; search: boolean; arrows: boolean; nodes: boolean }
export const defaultLayers: Layers = { streets: true, buildings: true, landmarks: true, search: true, arrows: false, nodes: false }
export function toggleLayer(layers: Layers, key: keyof Layers): Layers { return { ...layers, [key]: !layers[key] } }
export type RoadClass = 'major' | 'medium' | 'local' | 'minor'
export const roadStyles: Record<RoadClass, { color: string; weight: number; minZoom: number }> = {
  major: { color: '#b7ae92', weight: 4.5, minZoom: 14 },
  medium: { color: '#bcc0b7', weight: 3, minZoom: 15 },
  local: { color: '#c9cfc9', weight: 2, minZoom: 16 },
  minor: { color: '#d4d8d1', weight: 1.2, minZoom: 17 },
}
export function roadClass(value: RoadProperties['highway']): RoadClass {
  const types = Array.isArray(value) ? value : [value]
  if (types.some(type => /^(motorway|trunk|primary|secondary)(_link)?$/.test(type || ''))) return 'major'
  if (types.some(type => /^(tertiary|unclassified)(_link)?$/.test(type || ''))) return 'medium'
  if (types.includes('residential')) return 'local'
  return 'minor'
}
export function roadName(value: RoadProperties['name']): string | null {
  const names = (Array.isArray(value) ? value : [value]).filter((name): name is string => typeof name === 'string' && !!name.trim())
  return names.length ? [...new Set(names)].join(' / ') : null
}
export type LabelCandidate = { name: string; x: number; y: number; lat: number; lon: number; angle: number; rank: number; length: number }
export function selectStreetLabels(candidates: LabelCandidate[], width: number, height: number, blocked: { x: number; y: number; radius: number }[] = []): LabelCandidate[] {
  const selected: LabelCandidate[] = [], seen = new Set<string>()
  for (const candidate of [...candidates].sort((a, b) => a.rank - b.rank || b.length - a.length || a.name.localeCompare(b.name))) {
    const key = candidate.name.trim().toLocaleLowerCase('vi')
    const halfWidth = Math.min(100, candidate.name.length * 3.2)
    if (seen.has(key) || candidate.x < halfWidth + 12 || candidate.x > width - halfWidth - 12 || candidate.y < 30 || candidate.y > height - 70) continue
    if (blocked.some(p => Math.abs(p.x - candidate.x) < halfWidth + p.radius && Math.abs(p.y - candidate.y) < 16 + p.radius)) continue
    if (selected.some(p => Math.abs(p.x - candidate.x) < halfWidth + Math.min(100, p.name.length * 3.2) + 14 && Math.abs(p.y - candidate.y) < 34)) continue
    seen.add(key); selected.push(candidate)
    if (selected.length === 28) break
  }
  return selected
}
export function parseContext(value: unknown): MapContext {
  if (!value || typeof value !== 'object' || !('type' in value) || value.type !== 'FeatureCollection' || !('features' in value) || !Array.isArray(value.features) || !('counts' in value) || !('center' in value)) throw new Error('Invalid local map context')
  const context = value as MapContext
  if (!context.center || !Number.isFinite(context.center.lat) || !Number.isFinite(context.center.lon) || !context.counts || !Number.isInteger(context.counts.buildings) || !Number.isInteger(context.counts.pois) || context.counts.buildings < 0 || context.counts.pois < 0 || context.features.some(f => !f || f.type !== 'Feature' || !f.geometry || !f.properties)) throw new Error('Invalid local map context')
  return context
}
