import { useEffect, useMemo, useRef, useState } from 'react'
import { simulateContinuousBar } from '../api/bar'
import { errorText } from '../api/client'
import type { ContinuousBarResponse, SensedRegion, WorldPoint } from '../types/barContinuous'
import { buildContinuousPlayback, interpolatedPose } from './barContinuousPlayback'

function regionPath(region: SensedRegion, y: (value: number) => number): string {
  const polygons = region.type === 'Polygon'
    ? [region.coordinates as number[][][]]
    : region.coordinates as number[][][][]
  return polygons.map(polygon => polygon.map(ring => ring.map(([x, ordinate], index) =>
    `${index === 0 ? 'M' : 'L'}${x},${y(ordinate)}`).join(' ') + ' Z').join(' ')).join(' ')
}

function pointsPath(points: WorldPoint[], y: (value: number) => number): string {
  return points.map((point, index) => `${index ? 'L' : 'M'}${point.x},${y(point.y)}`).join(' ')
}

export function ContinuousBarPage() {
  const [scenario, setScenario] = useState<'irregular_u' | 'irregular_bugtrap'>('irregular_u')
  const [radius, setRadius] = useState(6)
  const [result, setResult] = useState<ContinuousBarResponse | null>(null)
  const [playhead, setPlayhead] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const clock = useRef<number | null>(null)
  const lastTime = useRef<number | null>(null)
  const viewport = useRef<HTMLDivElement>(null)
  const timeline = useMemo(() => result ? buildContinuousPlayback(result) : [], [result])
  const index = Math.min(result ? result.frames.length - 1 : 0, Math.floor(playhead))
  const frame = result?.frames[index]
  const state = timeline[index]
  const pose = result ? interpolatedPose(result.frames, playhead) : null
  const nextRecovery = result?.frames.findIndex((item, position) => position > index && item.event === 'recover_start') ?? -1

  useEffect(() => {
    if (!playing || !result) return
    const tick = (time: number) => {
      const elapsed = lastTime.current === null ? 0 : Math.min(100, time - lastTime.current)
      lastTime.current = time
      setPlayhead(previous => {
        const next = Math.min(result.frames.length - 1, previous + elapsed * speed / 220)
        if (next >= result.frames.length - 1) setPlaying(false)
        return next
      })
      clock.current = requestAnimationFrame(tick)
    }
    clock.current = requestAnimationFrame(tick)
    return () => {
      if (clock.current !== null) cancelAnimationFrame(clock.current)
      lastTime.current = null
    }
  }, [playing, result, speed])

  async function run() {
    setBusy(true)
    setError('')
    setPlaying(false)
    setResult(null)
    setPlayhead(0)
    try {
      setResult(await simulateContinuousBar(scenario, radius))
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setBusy(false)
    }
  }

  function changeZoom(value: number) {
    setZoom(Math.max(1, Math.min(3, value)))
    if (viewport.current && value <= 1) {
      viewport.current.scrollLeft = 0
      viewport.current.scrollTop = 0
    }
  }

  const bounds = result?.bounds ?? [0, 0, 40, 40]
  const [x0, y0, x1, y1] = bounds
  const y = (value: number) => result?.y_axis === 'down' ? value : y0 + y1 - value
  const worldHeight = y1 - y0
  const worldWidth = x1 - x0
  const robotHeading = pose ? (result?.y_axis === 'down' ? pose.heading : -pose.heading) * 180 / Math.PI : 0
  const svgSize = Math.max(660, worldWidth * 18) * zoom
  const metric = result?.metrics

  return <main className="page bar-page continuous-bar-page">
    <div className="page-top"><div><p className="eyebrow">01 / CONTINUOUS NAVIGATION</p><h1>Blind-Alley Robot Navigation</h1><p>360° limited sensing, arbitrary-angle motion, and repeated C++ A* on verified free space.</p></div><span className="status-pill">Continuous 2D · point robot</span></div>
    <div className="robot-layout bar-layout">
      <aside className="control-panel bar-control">
        <div className="panel-title"><h2>Mission setup</h2><span>Polygon worlds</span></div>
        <label className="select-field">Map<select value={scenario} onChange={event => { setScenario(event.target.value as typeof scenario); setResult(null); setPlaying(false) }}><option value="irregular_u">Irregular U · 40 × 40</option><option value="irregular_bugtrap">Polygon bugtrap · 48 × 48</option></select></label>
        <p className="bar-scenario-description">Obstacles use the imported polygon coordinates. The robot sees only geometry reached by its sensor.</p>
        <label className="select-field">Sensor radius (world units)<input type="number" min="1" max="10" step="0.5" value={radius} onChange={event => { setRadius(Number(event.target.value)); setResult(null); setPlaying(false) }} /></label>
        <button type="button" className="primary full" disabled={busy || radius < 1 || radius > 10} onClick={() => void run()}>{busy ? 'Simulating…' : 'Run simulation'}</button>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="panel-divider" />
        <p className="aside-explain">A holonomic point robot moves on straight segments through sensed, certified free space. Goal and scenario bounds are known; hidden obstacles are not.</p>
        <div className="bar-control-note"><strong>Recovery rule</strong><span>When a local exploration branch has no useful candidate, A* plans a return through known free space. A reversed executed entry trail is the verified fallback.</span></div>
      </aside>
      <section className="robot-workspace bar-workspace" aria-label="Continuous robot simulation">
        <div className="workspace-bar"><strong>Discovered polygon world</strong><span>{result ? `${worldWidth} × ${worldHeight} units · ${result.sensor_fov_degrees}° sensor` : 'World initially unknown'}</span></div>
        {result && frame && state && pose && <div className="bar-live-status"><div className="bar-event" data-event={frame.event}><small>{frame.event.replace('_', ' ')}</small><strong>{frame.event === 'recover_start' ? frame.fallback ? 'Reverse the entry trail' : 'A* planned the return' : frame.event === 'recover_end' ? 'Recovery verified' : frame.event === 'plan' ? 'A* plans in known free space' : frame.event === 'sense' ? '360° sensing' : frame.event === 'finish' ? result.status.replaceAll('_', ' ') : 'Continuous movement'}</strong><span>{frame.event === 'sense' ? `${(frame.new_area ?? 0).toFixed(2)} new square units certified` : frame.event === 'recover_end' ? `Retreat ${frame.retreat_length?.toFixed(2)} / entry ${frame.entry_length?.toFixed(2)}` : `Position (${pose.position.x.toFixed(2)}, ${pose.position.y.toFixed(2)})`}</span></div><div className="bar-live-counts"><div><small>Distance</small><strong>{state.distance.toFixed(1)}</strong></div><div><small>Recoveries</small><strong>{state.recoveries}</strong></div><div><small>Frame</small><strong>{index + 1} / {result.frames.length}</strong></div></div></div>}
        <div className="continuous-map-stage" ref={viewport}>
          {result && state && pose ? <svg role="img" aria-label="Discovered continuous robot map" className="continuous-map" style={{ width: svgSize, height: svgSize * worldHeight / worldWidth }} viewBox={`${x0} ${y0} ${worldWidth} ${worldHeight}`}>
            <rect x={x0} y={y0} width={worldWidth} height={worldHeight} className="continuous-unknown" />
            {state.regions.map((region, regionIndex) => <path key={regionIndex} d={regionPath(region, y)} className="continuous-free" fillRule="evenodd" />)}
            {state.edges.map(([a, b], edgeIndex) => <path key={edgeIndex} d={pointsPath([a, b], y)} className="continuous-obstacle" />)}
            <path d={pointsPath(state.trail, y)} className="continuous-trail" />
            {state.entry.length > 1 && <path d={pointsPath(state.entry, y)} className="continuous-entry" />}
            {state.retreat.length > 0 && <path d={pointsPath([state.trail[state.trail.length - state.retreat.length - 1], ...state.retreat], y)} className="continuous-retreat" />}
            {state.path.length > 1 && <path d={pointsPath(state.path, y)} className="continuous-plan" />}
            {state.target && <circle cx={state.target.x} cy={y(state.target.y)} r="0.42" className="continuous-target" />}
            <circle cx={result.start.x} cy={y(result.start.y)} r="0.42" className="continuous-start" />
            <circle cx={result.goal.x} cy={y(result.goal.y)} r="0.52" className="continuous-goal" />
            <circle cx={pose.position.x} cy={y(pose.position.y)} r={radius} className="continuous-sensor" />
            <g transform={`translate(${pose.position.x} ${y(pose.position.y)}) rotate(${robotHeading})`} className="continuous-robot"><circle r="0.49" /><path d="M 0.16,-0.28 L 0.75,0 L 0.16,0.28 Z" /></g>
          </svg> : <div className="bar-empty"><strong>Ready to explore</strong><span>Run a simulation to reveal the continuous polygon world.</span></div>}
        </div>
        <div className="bar-map-tools"><div className="bar-zoom"><span>View</span><button type="button" aria-label="Zoom out" disabled={!result || zoom <= 1} onClick={() => changeZoom(zoom - 0.25)}>−</button><button type="button" disabled={!result} onClick={() => changeZoom(1)}>Fit</button><button type="button" aria-label="Zoom in" disabled={!result || zoom >= 3} onClick={() => changeZoom(zoom + 0.25)}>+</button><small>{Math.round(zoom * 100)}%</small></div><span className="bar-pan-hint">Scroll the map to pan when zoomed</span></div>
        {result && <div className="bar-playback"><div className="bar-playback-buttons"><button type="button" onClick={() => { if (index >= result.frames.length - 1) setPlayhead(0); setPlaying(value => !value) }}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => { setPlaying(false); setPlayhead(Math.min(index + 1, result.frames.length - 1)) }}>Step</button><button type="button" onClick={() => { setPlaying(false); setPlayhead(0) }}>Restart</button><button type="button" disabled={nextRecovery < 0} onClick={() => { setPlaying(false); setPlayhead(nextRecovery) }}>Next recovery</button></div><label className="bar-speed">Speed<select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value={1}>Careful</option><option value={2}>Normal</option><option value={5}>Fast</option><option value={12}>Overview</option></select></label><label className="bar-scrubber">Frame {index + 1} / {result.frames.length}<input aria-label="Playback frame" type="range" min="0" max={result.frames.length - 1} value={index} onChange={event => { setPlaying(false); setPlayhead(Number(event.target.value)) }} /></label></div>}
        <div className="grid-legend bar-legend"><span><i className="dot bar-unknown" />Unknown</span><span><i className="dot bar-free" />Certified free</span><span><i className="dot obstacle" />Observed obstacle</span><span><i className="dot path" />A* path</span><span><i className="dot bar-entry" />Entry</span><span><i className="dot bar-retreat" />Retreat</span><span><i className="dot robot" />Robot / goal</span></div>
      </section>
    </div>
    {result && index === result.frames.length - 1 && metric && <section className="bar-summary"><div className="section-heading"><h2>Episode result</h2><span>{result.status.replaceAll('_', ' ')}</span></div><p className="notice">{result.success ? 'Goal reached.' : 'Goal not reached in this bounded exploration run.'} {result.recoveries.length} branch returns verified against their recorded continuous entry trajectories.</p><div className="bar-metrics"><div><small>Executed distance</small><strong>{metric.executed_distance.toFixed(2)} units</strong></div><div><small>Turns</small><strong>{metric.turn_count}</strong></div><div><small>A* calls</small><strong>{metric.replanning_count}</strong></div><div><small>Expanded nodes</small><strong>{metric.astar_expanded_nodes}</strong></div><div><small>Planning time</small><strong>{metric.planning_time_ms.toFixed(3)} ms</strong></div><div><small>Largest graph</small><strong>{metric.max_graph_nodes} nodes / {metric.max_graph_edges} edges</strong></div></div><p className="muted">Turns count heading changes between executed segments. Return bounds apply to locally exhausted branches, not arbitrary polygonal BARs.</p></section>}
  </main>
}
