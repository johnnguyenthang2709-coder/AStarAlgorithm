import { useEffect, useMemo, useState } from 'react'
import L from 'leaflet'
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMap, useMapEvents, Pane } from 'react-leaflet'
import type { Coordinate, TraceEvent } from '../types/common'
import type { RoadNode, RoadSearchResponse, RoadSnap } from '../types/road'
import type { PickMode, Selection } from './selection'
import { SearchLayer } from './SearchLayer'
import { roadContext, roadGeometry } from '../api/road'
import { CartographyLayer } from './CartographyLayer'
import { MapLayersControl } from './MapLayersControl'
import { defaultLayers, toggleLayer, type Layers, type MapContext, type RoadGeometry } from './cartography'

const center: [number, number] = [10.7729730556, 106.6591888889]
const emptyRoute: Coordinate[] = []
function ClickPicker({ mode, onPick }: { mode: PickMode; onPick: (point: Coordinate) => void }) {
  useMapEvents({ click: event => { if (mode) onPick({ lat: event.latlng.lat, lon: event.latlng.lng }) } })
  return null
}
function RouteFit({ route }: { route: Coordinate[] }) {
  const map = useMap()
  useEffect(() => { if (route.length > 1) map.fitBounds(route.map(point => [point.lat, point.lon] as [number, number]), { padding: [55, 55], maxZoom: 17 }) }, [route, map])
  return null
}
function Scale() {
  const map = useMap()
  useEffect(() => { const scale = L.control.scale({ imperial: false, position: 'bottomleft', maxWidth: 110 }).addTo(map); return () => { scale.remove() } }, [map])
  return null
}
function CampusAnchor({ picking, point }: { picking: boolean; point: Coordinate }) {
  const map = useMap()
  useEffect(() => {
    const label = document.createElement('div'); label.className = 'campus-anchor'
    const title = document.createElement('strong'), caption = document.createElement('span')
    title.textContent = 'HCMUT'; caption.textContent = 'Campus 1'; label.append(title, caption)
    const marker = L.marker([point.lat, point.lon], { pane: 'landmarks', interactive: !picking, bubblingMouseEvents: true, icon: L.divIcon({ html: label, className: 'cartographic-icon', iconSize: [100, 40], iconAnchor: [50, 20] }) }).addTo(map)
    const detail = document.createElement('div'); detail.textContent = 'Ho Chi Minh City University of Technology · Campus 1. Configured extraction anchor; no campus boundary is inferred.'
    marker.bindPopup(detail)
    return () => { marker.remove() }
  }, [map, picking, point.lat, point.lon])
  return null
}
function Point({ point, label, color }: { point: Coordinate; label: string; color: string }) {
  return <CircleMarker pane="endpoints" center={[point.lat, point.lon]} radius={9} pathOptions={{ color: '#fff', weight: 3, fillColor: color, fillOpacity: 1 }}><Tooltip pane="endpointLabels" direction="top" permanent className="endpoint-label">{label}</Tooltip></CircleMarker>
}
function SnapConnector({ requested, snapped }: { requested: Coordinate; snapped?: RoadSnap }) {
  if (!snapped || snapped.snap_distance_m < 4) return null
  return <Polyline pane="endpoints" positions={[[requested.lat, requested.lon], [snapped.lat, snapped.lon]]} pathOptions={{ color: '#61748a', dashArray: '3 5', weight: 2 }} />
}
export function RoadMap({ selection, pickMode, onPick, startSnap, goalSnap, result, events, index, nodes }: { selection: Selection; pickMode: PickMode; onPick: (point: Coordinate) => void; startSnap: RoadSnap | null; goalSnap: RoadSnap | null; result: RoadSearchResponse | null; events: TraceEvent<number>[]; index: number; nodes: RoadNode[] }) {
  const [tileFailed, setTileFailed] = useState(false)
  const [roads, setRoads] = useState<RoadGeometry | null>(null)
  const [context, setContext] = useState<MapContext | null>(null)
  const [contextError, setContextError] = useState(false)
  const [roadsError, setRoadsError] = useState(false)
  const [layers, setLayers] = useState<Layers>(defaultLayers)
  useEffect(() => {
    let active = true
    roadGeometry().then(value => { if (active) setRoads(value) }).catch(() => { if (active) setRoadsError(true) })
    roadContext().then(value => { if (active) setContext(value) }).catch(() => { if (active) setContextError(true) })
    return () => { active = false }
  }, [])
  const geometry = result?.route?.geometry ?? emptyRoute
  const markerSelection = useMemo(() => ({ start: startSnap ?? selection.start, goal: goalSnap ?? selection.goal }), [startSnap, goalSnap, selection])
  return <div className={`map-shell ${pickMode ? 'map-picking' : ''}`}>
    <MapContainer center={center} zoom={15} minZoom={11} scrollWheelZoom className="road-map">
      <Pane name="mapContext" style={{ zIndex: 330 }} />
      <Pane name="localRoads" style={{ zIndex: 390 }} />
      <Pane name="graphNodes" style={{ zIndex: 410 }} />
      <Pane name="roadArrows" style={{ zIndex: 420, pointerEvents: 'none' }} />
      <Pane name="streetLabels" style={{ zIndex: 450, pointerEvents: 'none' }} />
      <Pane name="landmarks" style={{ zIndex: 460 }} />
      <Pane name="searchStates" style={{ zIndex: 610, pointerEvents: 'none' }} />
      <Pane name="route" style={{ zIndex: 640, pointerEvents: 'none' }} />
      <Pane name="endpoints" style={{ zIndex: 650 }} />
      <Pane name="endpointLabels" style={{ zIndex: 660, pointerEvents: 'none' }} />
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' maxZoom={19} eventHandlers={{ tileerror: () => setTileFailed(true) }} />
      {roads && <CartographyLayer roads={roads} context={context} layers={layers} offline={tileFailed} selection={markerSelection} route={geometry} picking={!!pickMode} />}
      <CampusAnchor picking={!!pickMode} point={context?.center ?? { lat: center[0], lon: center[1] }} /><Scale />
      <ClickPicker mode={pickMode} onPick={onPick} />
      {layers.search && <SearchLayer events={events} index={index} nodes={nodes} />}
      {geometry.length > 1 && <><Polyline pane="route" positions={geometry.map(point => [point.lat, point.lon])} pathOptions={{ color: '#fff', weight: 10, opacity: .95 }} /><Polyline pane="route" positions={geometry.map(point => [point.lat, point.lon])} pathOptions={{ color: '#1766bd', weight: 5.5, opacity: 1 }} /><RouteFit route={geometry} /></>}
      {selection.start && <><Point point={startSnap ?? selection.start} label="Start" color="#177d60" /><SnapConnector requested={selection.start} snapped={startSnap ?? undefined} /></>}
      {selection.goal && <><Point point={goalSnap ?? selection.goal} label="Destination" color="#b7443f" /><SnapConnector requested={selection.goal} snapped={goalSnap ?? undefined} /></>}
    </MapContainer>
    <MapLayersControl layers={layers} buildingsAvailable={!!context?.counts.buildings} onToggle={key => setLayers(old => toggleLayer(old, key))} />
    {pickMode && <div className="map-prompt">Click the map to set {pickMode === 'start' ? 'start' : 'destination'}</div>}
    {(tileFailed || roadsError || contextError) && <div className="tile-notice">{roadsError ? 'Local map unavailable' : tileFailed ? roads ? 'Offline map · local OSM roads' : 'Loading local road map' : 'Landmark data unavailable'}</div>}
    <div className="map-legend" aria-label="Map legend"><span><i className="dot start" />Start</span><span><i className="dot goal" />Destination</span><span><i className="dot frontier" />Frontier</span><span><i className="dot expanded" />Expanded</span><span><i className="line path" />Final path</span></div>
  </div>
}
