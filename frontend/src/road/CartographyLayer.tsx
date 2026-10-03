import { useEffect, useState } from 'react'
import L from 'leaflet'
import { useMap, useMapEvents } from 'react-leaflet'
import type { Coordinate } from '../types/common'
import type { Selection } from './selection'
import { roadClass, roadName, roadStyles, selectStreetLabels, type LabelCandidate, type Layers, type MapContext, type RoadFeature, type RoadGeometry } from './cartography'

function textIcon(text: string, className: string, angle = 0) {
  const element = document.createElement('span')
  element.className = className; element.textContent = text
  element.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`
  return L.divIcon({ html: element, className: 'cartographic-icon', iconSize: [0, 0], iconAnchor: [0, 0] })
}
function roadPopup(feature: RoadFeature) {
  const p = feature.properties, panel = document.createElement('div')
  panel.className = 'road-info'
  const title = document.createElement('strong'); title.textContent = roadName(p.name) || 'Unnamed road'; panel.append(title)
  const rows = [['Road type', Array.isArray(p.highway) ? p.highway.join(', ') : p.highway || 'Not recorded'],
    ['Direction', p.oneway === true ? 'One-way' : p.oneway === false ? 'Two-way road' : 'Not recorded'],
    ['Segment length', `${p.length_m.toFixed(1)} m`], ['Directed edge', `${p.from} → ${p.to}`],
    ['OSM way', p.osmid === null ? 'Not recorded' : String(p.osmid)]]
  for (const [label, value] of rows) { const row = document.createElement('div'), name = document.createElement('span'), detail = document.createElement('b'); name.textContent = label; detail.textContent = value; row.append(name, detail); panel.append(row) }
  return panel
}
function midpoint(feature: RoadFeature, map: L.Map) {
  const coordinates = feature.geometry.coordinates
  const points = coordinates.map(([lon, lat]) => map.latLngToContainerPoint([lat, lon]))
  let length = 0
  const lengths = points.slice(1).map((point, i) => { const distance = point.distanceTo(points[i]); length += distance; return distance })
  let remaining = length / 2
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i] && lengths[i] > 0) {
      const t = remaining / lengths[i], a = points[i], b = points[i + 1]
      const pixel = L.point(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
      const location = map.containerPointToLatLng(pixel)
      const angle = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI
      return { x: pixel.x, y: pixel.y, lat: location.lat, lon: location.lng, angle, length }
    }
    remaining -= lengths[i]
  }
  return null
}

export function CartographyLayer({ roads, context, layers, offline, selection, route, picking }: { roads: RoadGeometry; context: MapContext | null; layers: Layers; offline: boolean; selection: Selection; route: Coordinate[]; picking: boolean }) {
  const map = useMap()
  const [revision, setRevision] = useState(0)
  useMapEvents({ moveend: () => setRevision(value => value + 1), zoomend: () => setRevision(value => value + 1) })
  useEffect(() => {
    const renderer = L.canvas({ pane: 'localRoads', padding: .3 })
    const layer = L.geoJSON(roads, { pane: 'localRoads', style: feature => {
      const style = roadStyles[roadClass(feature?.properties.highway)]
      return { renderer, color: style.color, weight: style.weight, opacity: offline ? 1 : .65, interactive: !picking }
    }, onEachFeature: (feature, line) => { if (!picking) line.bindPopup(roadPopup(feature as RoadFeature), { maxWidth: 300 }) } }).addTo(map)
    return () => { layer.remove(); renderer.remove() }
  }, [map, roads, offline, picking])
  useEffect(() => {
    const group = L.layerGroup().addTo(map), renderer = L.canvas({ pane: 'mapContext' })
    if (context && layers.buildings) {
      const buildings = { ...context, features: context.features.filter(f => !!f.properties.building) }
      L.geoJSON(buildings,
        { pane: 'mapContext', style: { renderer, color: '#c8cfc7', weight: .6, fillColor: '#dce1d8', fillOpacity: .65, interactive: false } }).addTo(group)
    }
    if (context && layers.landmarks) for (const feature of context.features.filter(f => f.properties.category && f.geometry.type === 'Point')) {
      if (feature.geometry.type !== 'Point') continue
      const [lon, lat] = feature.geometry.coordinates, p = feature.properties
      const symbols: Record<string, string> = { university: 'U', college: 'U', school: 'E', hospital: '+', clinic: '+', park: 'P', parking: 'P', fuel: 'F', bus_stop: 'B', platform: 'B', station: 'B', cafe: 'C' }
      const marker = L.marker([lat, lon], { pane: 'landmarks', title: p.name || p.category, interactive: !picking, bubblingMouseEvents: true, icon: textIcon(symbols[p.category!] || '•', `poi-symbol ${p.category}`) }).addTo(group)
      marker.getElement()?.setAttribute('aria-label', p.name || p.category!.replace('_', ' '))
      const detail = document.createElement('div'); detail.textContent = `${p.name || 'Unnamed place'} · ${p.category?.replace('_', ' ')} · OSM ${p.osm_id}`
      marker.bindPopup(detail)
      if (p.name && ['hospital', 'park'].includes(p.category!)) marker.bindTooltip(p.name, { permanent: map.getZoom() >= 15, direction: 'right', className: 'landmark-label', pane: 'streetLabels' })
    }
    return () => { group.remove(); renderer.remove() }
  }, [map, context, layers.buildings, layers.landmarks, revision, picking])
  useEffect(() => {
    const group = L.layerGroup().addTo(map), size = map.getSize(), zoom = map.getZoom()
    const blocked = [selection.start, selection.goal].filter((p): p is Coordinate => !!p).map(p => ({ ...map.latLngToContainerPoint([p.lat, p.lon]), radius: 45 }))
    const campus = context?.center ?? { lat: 10.7729730556, lon: 106.6591888889 }
    blocked.push({ ...map.latLngToContainerPoint([campus.lat, campus.lon]), radius: 45 })
    blocked.push({ x: size.x - 80, y: 75, radius: 85 }, { x: 25, y: 45, radius: 25 })
    // Reserve the whole visible route, including intermediate geometry vertices.
    for (let i = 1; i < route.length; i++) {
      const a = map.latLngToContainerPoint([route[i - 1].lat, route[i - 1].lon]), b = map.latLngToContainerPoint([route[i].lat, route[i].lon])
      const steps = Math.max(1, Math.ceil(a.distanceTo(b) / 15))
      for (let j = 0; j <= steps; j++) blocked.push({ x: a.x + (b.x - a.x) * j / steps, y: a.y + (b.y - a.y) * j / steps, radius: 12 })
    }
    const candidates: LabelCandidate[] = []
    if (layers.streets) for (const feature of roads.features) {
      const name = roadName(feature.properties.name), kind = roadClass(feature.properties.highway)
      if (!name || zoom < roadStyles[kind].minZoom) continue
      const point = midpoint(feature, map)
      if (!point || point.length < 35) continue
      candidates.push({ ...point, name, rank: ['major', 'medium', 'local', 'minor'].indexOf(kind), angle: point.angle > 90 ? point.angle - 180 : point.angle < -90 ? point.angle + 180 : point.angle })
    }
    for (const point of selectStreetLabels(candidates, size.x, size.y, blocked)) L.marker([point.lat, point.lon], { pane: 'streetLabels', interactive: false, keyboard: false, icon: textIcon(point.name, 'street-label', point.angle) }).addTo(group)
    if (layers.arrows && zoom >= 15) {
      const occupied = new Set<string>(), renderer = L.canvas({ pane: 'roadArrows' })
      let count = 0
      for (const feature of roads.features) {
        if (feature.properties.oneway !== true) continue
        const p = midpoint(feature, map)
        if (!p || p.length < 35 || p.x < 20 || p.x > size.x - 20 || p.y < 20 || p.y > size.y - 50) continue
        const key = `${Math.floor(p.x / 55)},${Math.floor(p.y / 55)}`
        if (occupied.has(key)) continue
        occupied.add(key)
        const angle = p.angle * Math.PI / 180, tip = L.point(p.x + 5 * Math.cos(angle), p.y + 5 * Math.sin(angle))
        const arms = [-1, 1].map(side => map.containerPointToLatLng(L.point(p.x - 4 * Math.cos(angle) + side * 4 * Math.sin(angle), p.y - 4 * Math.sin(angle) - side * 4 * Math.cos(angle))))
        L.polyline([arms[0], map.containerPointToLatLng(tip), arms[1]], { pane: 'roadArrows', renderer, color: '#6e807b', weight: 1.6, interactive: false }).addTo(group)
        if (++count >= 100) break
      }
      group.on('remove', () => renderer.remove())
    }
    return () => { group.remove() }
  }, [map, roads, context, layers.streets, layers.arrows, revision, selection, route])
  useEffect(() => {
    if (!layers.nodes) return
    const group = L.layerGroup().addTo(map), renderer = L.canvas({ pane: 'graphNodes' }), seen = new Set<number>()
    for (const feature of roads.features) {
      const coords = feature.geometry.coordinates
      for (const [id, xy] of [[feature.properties.from, coords[0]], [feature.properties.to, coords[coords.length - 1]]] as [number, number[]][]) {
        if (seen.has(id)) continue
        seen.add(id)
        L.circleMarker([xy[1], xy[0]], { pane: 'graphNodes', renderer, radius: 2, weight: .6, color: '#76867d', fillOpacity: .7 }).bindTooltip(`Graph node ${id}`).addTo(group)
      }
    }
    return () => { group.remove(); renderer.remove() }
  }, [map, roads, layers.nodes])
  return null
}
