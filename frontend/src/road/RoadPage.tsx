import { useEffect, useMemo, useRef, useState } from 'react'
import { roadCompare, roadNodes, roadSearch, roadSnap } from '../api/road'
import { errorText } from '../api/client'
import type { Algorithm, Coordinate } from '../types/common'
import type { Health, RoadCompareResponse, RoadNode, RoadSearchResponse, RoadSnap } from '../types/road'
import { distance } from '../utils/format'
import { SearchMetricsView } from '../components/Metric'
import { PlaybackControls } from '../components/PlaybackControls'
import { AlgorithmInspector } from '../components/AlgorithmInspector'
import { useTracePlayback } from '../hooks/useTracePlayback'
import { RoadMap } from './RoadMap'
import { ComparisonPanel } from './ComparisonPanel'
import { selectPoint, type PickMode, type Selection } from './selection'

export function RoadPage({ health, healthError }: { health: Health | null; healthError: string | null }) {
  const [selection, setSelection] = useState<Selection>({ start: null, goal: null })
  const [pickMode, setPickMode] = useState<PickMode>(null)
  const [startSnap, setStartSnap] = useState<RoadSnap | null>(null)
  const [goalSnap, setGoalSnap] = useState<RoadSnap | null>(null)
  const [algorithm, setAlgorithm] = useState<Algorithm>('astar')
  const [result, setResult] = useState<RoadSearchResponse | null>(null)
  const [comparison, setComparison] = useState<RoadCompareResponse | null>(null)
  const [nodes, setNodes] = useState<RoadNode[]>([])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const snapRequest = useRef({ start: 0, goal: 0 })
  const operation = useRef(0)
  const nodesRequested = useRef(false)
  const playback = useTracePlayback(result?.trace ?? [])
  const traceNodes = useMemo(() => [...nodes, ...(result?.trace_nodes ?? [])], [nodes, result?.trace_nodes])
  const unavailable = !!healthError || (health !== null && !health.road_graph_loaded)
  useEffect(() => {
    if (result?.trace.length && !nodes.length && !nodesRequested.current) {
      nodesRequested.current = true
      roadNodes().then(setNodes).catch(e => { nodesRequested.current = false; setError(errorText(e)) })
    }
  }, [result, nodes.length])
  async function choose(point: Coordinate, mode: Exclude<PickMode, null>) {
    const requestId = ++snapRequest.current[mode]
    operation.current++; playback.restart(); setBusy('')
    setSelection(old => selectPoint(old, mode, point)); setPickMode(null); setResult(null); setComparison(null); setError('')
    if (mode === 'start') setStartSnap(null); else setGoalSnap(null)
    try { const snapped = await roadSnap(point); if (snapRequest.current[mode] !== requestId) return; if (mode === 'start') setStartSnap(snapped); else setGoalSnap(snapped) } catch (e) { if (snapRequest.current[mode] === requestId) setError(errorText(e)) }
  }
  async function run(trace: boolean) {
    if (!selection.start || !selection.goal || busy) return
    const requestId = ++operation.current
    playback.pause()
    setBusy(trace ? 'Loading search trace…' : 'Finding route…'); setError(''); setComparison(null)
    try { const response = await roadSearch({ start: selection.start, goal: selection.goal, algorithm, trace }); if (operation.current === requestId) { setResult(response); setStartSnap(response.start.snapped); setGoalSnap(response.goal.snapped) } } catch (e) { if (operation.current === requestId) setError(errorText(e)) } finally { if (operation.current === requestId) setBusy('') }
  }
  async function compare() {
    if (!selection.start || !selection.goal || busy) return
    const requestId = ++operation.current
    setBusy('Comparing algorithms…'); setError('')
    try { const response = await roadCompare(selection.start, selection.goal); if (operation.current === requestId) { setComparison(response); setStartSnap(response.start.snapped); setGoalSnap(response.goal.snapped) } } catch (e) { if (operation.current === requestId) setError(errorText(e)) } finally { if (operation.current === requestId) setBusy('') }
  }
  function clear() { operation.current++; playback.restart(); setResult(null); setComparison(null); setError(''); setBusy('') }
  function reset() { clear(); snapRequest.current.start++; snapRequest.current.goal++; setSelection({ start: null, goal: null }); setStartSnap(null); setGoalSnap(null); setPickMode(null) }
  const ready = !!selection.start && !!selection.goal && !unavailable && !busy
  return <main className="page road-page"><div className="page-top"><div><p className="eyebrow">01 / IRREGULAR DIRECTED GRAPH</p><h1>Road Navigation</h1><p>Find a shortest-distance route around HCMUT Campus 1.</p></div><span className="status-pill">{health?.road_graph_loaded ? `${health.road_nodes.toLocaleString()} nodes · ${health.road_edges.toLocaleString()} edges` : 'Road data unavailable'}</span></div>
    <div className="road-layout"><aside className="control-panel"><div className="panel-title"><h2>Plan a route</h2><span>HCMUT · Ho Chi Minh City</span></div>
      <div className="field-block"><div className="field-heading"><span className="number-badge start">A</span><strong>Start</strong><button type="button" className={pickMode === 'start' ? 'small active' : 'small'} onClick={() => setPickMode('start')} disabled={unavailable}>Select on map</button></div><CoordinateFields key={`start:${selection.start?.lat},${selection.start?.lon}`} kind="Start" point={selection.start} disabled={unavailable} onSubmit={point => choose(point, 'start')} /><p className="field-note">{startSnap ? `Road ${startSnap.from_node ?? startSnap.node_id} → ${startSnap.to_node ?? startSnap.node_id} · snap ${distance(startSnap.snap_distance_m)}` : 'Choose a point or enter coordinates.'}</p></div>
      <div className="field-block"><div className="field-heading"><span className="number-badge goal">B</span><strong>Destination</strong><button type="button" className={pickMode === 'goal' ? 'small active' : 'small'} onClick={() => setPickMode('goal')} disabled={unavailable}>Select on map</button></div><CoordinateFields key={`goal:${selection.goal?.lat},${selection.goal?.lon}`} kind="Destination" point={selection.goal} disabled={unavailable} onSubmit={point => choose(point, 'goal')} /><p className="field-note">{goalSnap ? `Road ${goalSnap.from_node ?? goalSnap.node_id} → ${goalSnap.to_node ?? goalSnap.node_id} · snap ${distance(goalSnap.snap_distance_m)}` : 'Choose a point or enter coordinates.'}</p></div>
      <label className="select-field">Algorithm<select value={algorithm} onChange={e => { setAlgorithm(e.target.value as Algorithm); clear() }}><option value="astar">A* search</option><option value="dijkstra">Dijkstra</option></select></label>
      <button type="button" className="primary full" onClick={() => run(false)} disabled={!ready}>Find route</button>
      <div className="action-row"><button type="button" onClick={clear}>Clear route</button><button type="button" onClick={reset}>Reset points</button></div>
      <div className="panel-divider" /><p className="aside-explain">Distance only. Dijkstra is A* with h(n) = 0. The route follows the local road graph.</p>
      {busy && <p role="status" className="notice">{busy}</p>}{error && <p role="alert" className="error">{error}</p>}{unavailable && <p role="alert" className="error">{healthError || 'Road graph unavailable. Robot Lab is still usable.'}</p>}
    </aside><RoadMap selection={selection} pickMode={pickMode} onPick={point => { if (pickMode) void choose(point, pickMode) }} startSnap={startSnap} goalSnap={goalSnap} result={result} events={result?.trace ?? []} index={playback.index} nodes={traceNodes} /></div>
    <div className="results"><section className="result-summary"><div className="section-heading"><h2>Search result</h2><span>{result ? (result.found ? 'Route found' : 'No route') : 'Awaiting route'}</span></div>{result ? result.found && result.route ? <><div className="hero-metric"><small>Shortest-distance route</small><strong>{distance(result.route.cost_m)}</strong><span>{result.route.edge_path.length} road segments</span></div><SearchMetricsView metrics={result.metrics} /></> : <p className="empty-note">No route exists between the selected snapped road positions. Adjust a point and try again.</p> : <p className="empty-note">Select start and destination, then find a route. Search metrics come directly from the C++ engine.</p>}</section>
      <section className="trace-panel"><div className="section-heading"><h2>Search playback</h2><span>Trace from backend</span></div><p className="muted">Watch frontier discovery and expansions across the road network. A CLOSE event ends one expansion; a better path may reopen a state.</p><div className="action-row"><button type="button" onClick={() => run(true)} disabled={!ready}>Visualize search</button><button type="button" onClick={compare} disabled={!ready}>Compare Dijkstra</button></div>{result?.trace.length ? <><PlaybackControls playback={playback} total={result.trace.length} /><AlgorithmInspector event={playback.current} index={playback.index} stateLabel={state => `Node ${state}`} /></> : <p className="muted">Request a trace to enable playback.</p>}</section>
      {comparison && <ComparisonPanel result={comparison} />}</div>
  </main>
}
function CoordinateFields({ kind, point, onSubmit, disabled }: { kind: 'Start' | 'Destination'; point: Coordinate | null; onSubmit: (point: Coordinate) => void; disabled: boolean }) {
  const [lat, setLat] = useState(point?.lat.toFixed(6) ?? ''), [lon, setLon] = useState(point?.lon.toFixed(6) ?? '')
  return <form className="coordinate-fields" onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const latitude = (form.elements.namedItem('lat') as HTMLInputElement).value; const longitude = (form.elements.namedItem('lon') as HTMLInputElement).value; const a = Number(latitude), b = Number(longitude); if (latitude && longitude && a >= -90 && a <= 90 && b >= -180 && b <= 180) onSubmit({ lat: a, lon: b }) }}><label>Latitude<input name="lat" aria-label={`${kind} latitude`} type="number" step="any" min="-90" max="90" value={lat} onChange={e => setLat(e.target.value)} placeholder="10.772973" disabled={disabled} required /></label><label>Longitude<input name="lon" aria-label={`${kind} longitude`} type="number" step="any" min="-180" max="180" value={lon} onChange={e => setLon(e.target.value)} placeholder="106.659189" disabled={disabled} required /></label><button type="submit" className="small" aria-label={`Set ${kind.toLowerCase()} coordinates`} disabled={disabled}>Set</button></form>
}
