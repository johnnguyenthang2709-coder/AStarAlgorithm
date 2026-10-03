import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { useMap } from 'react-leaflet'
import type { RoadNode } from '../types/road'
import type { TraceEvent } from '../types/common'
import { tracePhase } from '../utils/traceState'

export function SearchLayer({ events, index, nodes }: { events: TraceEvent<number>[]; index: number; nodes: RoadNode[] }) {
  const map = useMap()
  const frontier = useRef<L.LayerGroup | null>(null)
  const expanded = useRef<L.LayerGroup | null>(null)
  const current = useRef<L.CircleMarker | null>(null)
  const processed = useRef(0)
  const frontierMarkers = useRef(new Map<number, L.CircleMarker>())
  const expandedMarkers = useRef(new Map<number, L.CircleMarker>())
  const positions = useRef(new Map<number, RoadNode>())
  const renderedEvents = useRef(events)
  const renderedNodes = useRef(nodes)
  useEffect(() => { positions.current = new Map(nodes.map(node => [node.node_id, node])) }, [nodes])
  useEffect(() => {
    const f = L.layerGroup().addTo(map), e = L.layerGroup().addTo(map)
    frontier.current = f; expanded.current = e
    return () => { f.remove(); e.remove(); current.current?.remove(); current.current = null }
  }, [map])
  useEffect(() => {
    if (!frontier.current || !expanded.current) return
    if (index < processed.current || index === 0 || renderedEvents.current !== events || renderedNodes.current !== nodes) {
      frontier.current.clearLayers(); expanded.current.clearLayers(); current.current?.remove(); current.current = null
      frontierMarkers.current.clear(); expandedMarkers.current.clear(); processed.current = 0
    }
    renderedEvents.current = events; renderedNodes.current = nodes
    for (let i = processed.current; i < index; i++) {
      const event = events[i], point = positions.current.get(event.state)
      if (!point) continue
      const location: L.LatLngExpression = [point.lat, point.lon]
      if (tracePhase(event.type) === 'frontier') {
        const oldExpanded = expandedMarkers.current.get(event.state)
        if (oldExpanded) { expanded.current.removeLayer(oldExpanded); expandedMarkers.current.delete(event.state) }
        if (!frontierMarkers.current.has(event.state)) {
          const marker = L.circleMarker(location, { pane: 'searchStates', interactive: false, radius: 3, color: '#b17118', fillColor: '#efb94f', fillOpacity: .75, weight: 1 }).addTo(frontier.current!)
          frontierMarkers.current.set(event.state, marker)
        }
      }
      if (tracePhase(event.type) === 'expanded') {
        const old = frontierMarkers.current.get(event.state)
        if (old) { frontier.current.removeLayer(old); frontierMarkers.current.delete(event.state) }
        if (!expandedMarkers.current.has(event.state)) {
          const marker = L.circleMarker(location, { pane: 'searchStates', interactive: false, radius: 3, color: '#718092', fillColor: '#9ba7b4', fillOpacity: .6, weight: 1 }).addTo(expanded.current!)
          expandedMarkers.current.set(event.state, marker)
        }
      }
    }
    processed.current = index
    current.current?.remove(); current.current = null
    if (index > 0) {
      const point = positions.current.get(events[index - 1]?.state)
      if (point) current.current = L.circleMarker([point.lat, point.lon], { pane: 'searchStates', interactive: false, radius: 8, color: '#152b48', weight: 3, fillColor: '#ffffff', fillOpacity: 1 }).addTo(map)
    }
  }, [events, index, nodes, map])
  return null
}
