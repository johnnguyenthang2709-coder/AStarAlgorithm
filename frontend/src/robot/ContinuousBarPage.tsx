import { useEffect, useMemo, useRef, useState } from 'react'
import { simulateContinuousBar } from '../api/bar'
import { errorText } from '../api/client'
import type { ContinuousBarResponse, ContinuousScenario, IndoorOptions, MazeOptions, SensedRegion, WorldPoint } from '../types/barContinuous'
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
  const [scenario, setScenario] = useState<ContinuousScenario>('lab_exploration')
  const [radius, setRadius] = useState(5)
  const [maze, setMaze] = useState<MazeOptions>({ seed: 17, size: 5, corridor_width: 2.8,
    loop_rate: 0.08, dead_end_rate: 0.45, trap_count: 2, difficulty: 'normal', irregularity: 0.65 })
  const [indoor, setIndoor] = useState<IndoorOptions>({ seed: 41, indoor_layout: 'apartment' })
  const [customEndpoints, setCustomEndpoints] = useState(false)
  const [startRoom, setStartRoom] = useState<[number, number]>([4, 0])
  const [goalRoom, setGoalRoom] = useState<[number, number]>([0, 4])
  const [showGraph, setShowGraph] = useState(false)
  const [showFullTrail, setShowFullTrail] = useState(false)
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
      setResult(await simulateContinuousBar(scenario, radius,
        scenario === 'indoor_seeded' ? { ...indoor, debug_graph: showGraph } :
        scenario === 'maze_seeded' || scenario === 'lab_seeded' ? { ...maze, debug_graph: showGraph,
          start_cell: customEndpoints ? startRoom : null,
          goal_cell: customEndpoints ? goalRoom : null } : { debug_graph: showGraph }))
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
  const mazeMode = scenario.startsWith('maze_') || scenario.startsWith('lab_')
  const labyrinthMode = scenario.startsWith('lab_')
  const indoorMode = scenario.startsWith('indoor_')
  const metric = result?.metrics
  const blockedReturns = result?.recoveries.filter(item => item.trigger === 'graph_blocked_target').length ?? 0

  return <main className="page bar-page continuous-bar-page">
    <div className="page-top"><div><p className="eyebrow">01 / CONTINUOUS NAVIGATION</p><h1>Blind-Alley Robot Navigation</h1><p>360° limited sensing, arbitrary-angle motion, and repeated C++ A* on verified free space.</p></div><span className="status-pill">Continuous 2D · point robot</span></div>
    <div className="robot-layout bar-layout">
      <aside className="control-panel bar-control">
        <div className="panel-title"><h2>Mission setup</h2><span>Continuous worlds</span></div>
        <label className="select-field">Map<select value={scenario} onChange={event => { const next = event.target.value as ContinuousScenario; setScenario(next); setRadius(next === 'maze_hard' ? 7 : next.startsWith('maze_') || next.startsWith('lab_') || next.startsWith('indoor_') ? 5 : 6); setResult(null); setPlaying(false) }}><optgroup label="Indoor exploration"><option value="indoor_apartment">Small Apartment</option><option value="indoor_office">Office Building</option><option value="indoor_challenge">Indoor Maze Challenge</option><option value="indoor_seeded">Seeded indoor floor plan</option></optgroup><optgroup label="Maze 3 · irregular labyrinth"><option value="lab_exploration">Exploration Labyrinth</option><option value="lab_alley">Blind-Alley Labyrinth</option><option value="lab_complex">Complex Irregular Labyrinth</option><option value="lab_seeded">Generate from seed</option></optgroup><optgroup label="Earlier validated Maze 3"><option value="maze_showcase">Basic Exploration Maze</option><option value="maze_hard">Blind-Alley Recovery Maze</option><option value="maze_seeded">Original seeded maze</option></optgroup><optgroup label="Validated polygon baselines"><option value="irregular_u">Irregular U · 40 × 40</option><option value="irregular_bugtrap">Polygon bugtrap · 48 × 48</option></optgroup></select></label>
        <p className="bar-scenario-description">{indoorMode ? 'Rooms, doors, corridors and furniture emerge through limited sensing. Branch IDs describe observed exploration history, not hidden room labels.' : labyrinthMode ? 'Winding polygon corridors, branches and wall islands are revealed only by sensing.' : mazeMode ? 'Original room-based maze retained for comparison and regression.' : 'Original polygon-coordinate baseline; the robot sees only geometry reached by its sensor.'}</p>
        {scenario === 'indoor_seeded' && <div className="maze-settings"><label className="select-field">Floor plan<select value={indoor.indoor_layout} onChange={event => setIndoor({ ...indoor, indoor_layout: event.target.value as IndoorOptions['indoor_layout'] })}><option value="apartment">Apartment</option><option value="office">Office</option><option value="challenge">Indoor challenge</option></select></label><label className="select-field">Seed<input type="number" min="0" max="2147483647" value={indoor.seed} onChange={event => setIndoor({ ...indoor, seed: Number(event.target.value) })} /></label></div>}
        {(scenario === 'maze_seeded' || scenario === 'lab_seeded') && <div className="maze-settings">
          <label className="select-field">Seed<input type="number" min="0" max="2147483647" value={maze.seed} onChange={event => setMaze({ ...maze, seed: Number(event.target.value) })} /></label>
          <label className="select-field">Maze size<input type="number" min="4" max="8" value={maze.size} onChange={event => { const size = Number(event.target.value); setMaze({ ...maze, size }); setStartRoom([size-1, 0]); setGoalRoom([0, size-1]) }} /></label>
          <label className="select-field">Corridor width<input type="number" min="1.2" max={scenario === 'lab_seeded' ? '3.2' : '4.2'} step="0.1" value={maze.corridor_width} onChange={event => setMaze({ ...maze, corridor_width: Number(event.target.value) })} /></label>
          <label className="select-field">Loop rate<input type="number" min="0" max="0.35" step="0.01" value={maze.loop_rate} onChange={event => setMaze({ ...maze, loop_rate: Number(event.target.value) })} /></label>
          <label className="select-field">Preserve dead ends<input type="number" min="0" max="1" step="0.05" value={maze.dead_end_rate} onChange={event => setMaze({ ...maze, dead_end_rate: Number(event.target.value) })} /></label>
          <label className="select-field">Minimum traps<input type="number" min="1" max="8" value={maze.trap_count} onChange={event => setMaze({ ...maze, trap_count: Number(event.target.value) })} /></label>
          {scenario === 'lab_seeded' && <label className="select-field">Irregularity<input type="number" min="0" max="1" step="0.05" value={maze.irregularity} onChange={event => setMaze({ ...maze, irregularity: Number(event.target.value) })} /></label>}
          <label className="select-field maze-difficulty">Difficulty<select value={maze.difficulty} onChange={event => setMaze({ ...maze, difficulty: event.target.value as MazeOptions['difficulty'] })}><option value="easy">Easy · more loops</option><option value="normal">Normal</option><option value="hard">Hard · fewer loops</option></select></label>
          <label className="bar-frontier-toggle maze-endpoint-toggle"><input type="checkbox" checked={customEndpoints} onChange={event => setCustomEndpoints(event.target.checked)} /> Choose start / goal rooms</label>
          {customEndpoints && <><label className="select-field">Start row<input type="number" min="0" max={maze.size-1} value={startRoom[0]} onChange={event => setStartRoom([Number(event.target.value), startRoom[1]])} /></label><label className="select-field">Start column<input type="number" min="0" max={maze.size-1} value={startRoom[1]} onChange={event => setStartRoom([startRoom[0], Number(event.target.value)])} /></label><label className="select-field">Goal row<input type="number" min="0" max={maze.size-1} value={goalRoom[0]} onChange={event => setGoalRoom([Number(event.target.value), goalRoom[1]])} /></label><label className="select-field">Goal column<input type="number" min="0" max={maze.size-1} value={goalRoom[1]} onChange={event => setGoalRoom([goalRoom[0], Number(event.target.value)])} /></label></>}
        </div>}
        <label className="select-field">Sensor radius (world units)<input type="number" min="1" max="10" step="0.5" value={radius} onChange={event => { setRadius(Number(event.target.value)); setResult(null); setPlaying(false) }} /></label>
        <label className="bar-frontier-toggle"><input type="checkbox" checked={showGraph} onChange={event => { setShowGraph(event.target.checked); setResult(null); setPlaying(false) }} /> Visibility graph debug (next run)</label>
        <button type="button" className="primary full" disabled={busy || radius < 1 || radius > 10} onClick={() => void run()}>{busy ? 'Simulating…' : 'Run simulation'}</button>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="panel-divider" />
        <p className="aside-explain">A holonomic point robot moves on straight segments through sensed, certified free space. Goal and bounds are known; hidden walls, furniture and doorway locations are not. Generation does not prefilter layouts by policy success.</p>
        <div className="bar-control-note"><strong>Return rule</strong><span>When no reachable useful candidate remains, A* plans to the nearest ancestor with another branch. A graph-blocked target is deferred; the reversed entry trail remains the verified fallback.</span></div>
      </aside>
      <section className="robot-workspace bar-workspace" aria-label="Continuous robot simulation">
        <div className="workspace-bar"><strong>{indoorMode ? 'Indoor · discovered floor plan' : labyrinthMode ? 'Maze 3 · irregular labyrinth' : mazeMode ? 'Maze 3 · original room maze' : 'Discovered polygon world'}</strong><span>{result ? `${worldWidth} × ${worldHeight} units · ${result.sensor_fov_degrees}° sensor` : 'World initially unknown'}</span></div>
        {result && frame && state && pose && <div className="bar-live-status"><div className="bar-event" data-event={frame.event}><small>{frame.event.replace('_', ' ')}</small><strong>{frame.event === 'branch' ? frame.status === 'active' ? `Entered observed branch ${frame.branch_id}` : `Branch ${frame.branch_id} ${frame.status?.replaceAll('_', ' ')}` : frame.event === 'recover_start' ? frame.trigger === 'graph_blocked_target' ? frame.fallback ? 'Blocked target · reverse return' : 'Blocked target · A* return' : frame.fallback ? 'Reverse the entry trail' : 'A* planned the return' : frame.event === 'recover_end' ? 'Return bound verified' : frame.event === 'plan' ? frame.status === 'unreachable_target' ? 'Target unreachable on known graph' : 'A* plans in known free space' : frame.event === 'sense' ? '360° sensing' : frame.event === 'finish' ? result.status.replaceAll('_', ' ') : 'Continuous movement'}</strong><span>{frame.event === 'sense' ? `${(frame.new_area ?? 0).toFixed(2)} new square units certified` : frame.event === 'recover_end' ? `Return ${frame.retreat_length?.toFixed(2)} / entry ${frame.entry_length?.toFixed(2)}` : `Position (${pose.position.x.toFixed(2)}, ${pose.position.y.toFixed(2)})`}</span></div><div className="bar-live-counts">{indoorMode && <div><small>Observed branch</small><strong>{state.branchId ?? 0}</strong></div>}<div><small>Distance</small><strong>{state.distance.toFixed(1)}</strong></div><div><small>Returns</small><strong>{state.recoveries}</strong></div><div><small>Frame</small><strong>{index + 1} / {result.frames.length}</strong></div></div></div>}
        <div className={`continuous-map-stage ${labyrinthMode || indoorMode ? 'labyrinth-map-stage' : ''}`} ref={viewport}>
          {result && state && pose ? <svg role="img" aria-label="Discovered continuous robot map" className="continuous-map" style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }} viewBox={`${x0} ${y0} ${worldWidth} ${worldHeight}`}>
            <rect x={x0} y={y0} width={worldWidth} height={worldHeight} className="continuous-unknown" />
            {state.regions.map((region, regionIndex) => <path key={regionIndex} d={regionPath(region, y)} className="continuous-free" fillRule="evenodd" />)}
            {state.edges.map(([a, b], edgeIndex) => <path key={edgeIndex} d={pointsPath([a, b], y)} className="continuous-obstacle" fill="none" />)}
            {showGraph && state.graphLinks.map(([a, b], linkIndex) => <path key={`graph-${linkIndex}`} d={pointsPath([state.graphPoints[a], state.graphPoints[b]], y)} className="continuous-graph-link" fill="none" />)}
            {showGraph && state.graphPoints.map((point, pointIndex) => <circle key={`node-${pointIndex}`} cx={point.x} cy={y(point.y)} r="0.12" className="continuous-graph-node" />)}
            {showFullTrail && <path d={pointsPath(state.trail, y)} className="continuous-trail" fill="none" />}
            <path d={pointsPath(state.trail.slice(-8), y)} className="continuous-recent-trail" fill="none" />
            {state.entry.length > 1 && <path d={pointsPath(state.entry, y)} className="continuous-entry" fill="none" />}
            {state.retreat.length > 0 && <path d={pointsPath([state.trail[state.trail.length - state.retreat.length - 1], ...state.retreat], y)} className="continuous-retreat" fill="none" />}
            {state.path.length > 1 && <path d={pointsPath(state.path, y)} className="continuous-plan" fill="none" />}
            {state.target && <circle cx={state.target.x} cy={y(state.target.y)} r="0.42" className="continuous-target" />}
            <circle cx={result.start.x} cy={y(result.start.y)} r="0.42" className="continuous-start" />
            <circle cx={result.goal.x} cy={y(result.goal.y)} r="0.52" className="continuous-goal" />
            <circle cx={pose.position.x} cy={y(pose.position.y)} r={radius} className="continuous-sensor" />
            <g transform={`translate(${pose.position.x} ${y(pose.position.y)}) rotate(${robotHeading})`} className="continuous-robot"><circle r="0.49" /><path d="M 0.16,-0.28 L 0.75,0 L 0.16,0.28 Z" /></g>
          </svg> : <div className="bar-empty"><strong>Ready to explore</strong><span>Run a simulation to reveal the continuous polygon world.</span></div>}
        </div>
        <div className="bar-map-tools"><div className="bar-zoom"><span>View</span><button type="button" aria-label="Zoom out" disabled={!result || zoom <= 1} onClick={() => changeZoom(zoom - 0.25)}>−</button><button type="button" disabled={!result} onClick={() => changeZoom(1)}>Fit</button><button type="button" aria-label="Zoom in" disabled={!result || zoom >= 3} onClick={() => changeZoom(zoom + 0.25)}>+</button><small>{Math.round(zoom * 100)}%</small></div><label className="bar-frontier-toggle"><input type="checkbox" checked={showFullTrail} onChange={event => setShowFullTrail(event.target.checked)} /> Full executed trail</label><span className="bar-pan-hint">Scroll the map to pan when zoomed</span></div>
        {result && <div className="bar-playback"><div className="bar-playback-buttons"><button type="button" onClick={() => { if (index >= result.frames.length - 1) setPlayhead(0); setPlaying(value => !value) }}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => { setPlaying(false); setPlayhead(Math.min(index + 1, result.frames.length - 1)) }}>Step</button><button type="button" onClick={() => { setPlaying(false); setPlayhead(0) }}>Restart</button><button type="button" disabled={nextRecovery < 0} onClick={() => { setPlaying(false); setPlayhead(nextRecovery) }}>Next recovery</button></div><label className="bar-speed">Speed<select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value={1}>Careful</option><option value={2}>Normal</option><option value={5}>Fast</option><option value={12}>Overview</option></select></label><label className="bar-scrubber">Frame {index + 1} / {result.frames.length}<input aria-label="Playback frame" type="range" min="0" max={result.frames.length - 1} value={index} onChange={event => { setPlaying(false); setPlayhead(Number(event.target.value)) }} /></label></div>}
        <div className="grid-legend bar-legend"><span><i className="dot bar-unknown" />Unknown</span><span><i className="dot bar-free" />Certified free</span><span><i className="dot obstacle" />Observed wall</span><span><i className="dot path" />A* path</span><span><i className="dot bar-entry" />Entry</span><span><i className="dot bar-retreat" />Retreat</span><span><i className="dot robot" />Robot / goal</span></div>
      </section>
    </div>
        {result && index === result.frames.length - 1 && metric && <section className="bar-summary"><div className="section-heading"><h2>Episode result</h2><span>{result.status.replaceAll('_', ' ')}</span></div><p className="notice">{result.success ? 'Goal reached.' : 'Goal not reached in this bounded exploration run.'} {result.recoveries.length} returns verified against their recorded continuous entry trajectories; {blockedReturns} followed graph-blocked targets.</p><div className="bar-metrics"><div><small>Executed distance</small><strong>{metric.executed_distance.toFixed(2)} units</strong></div><div><small>Turns</small><strong>{metric.turn_count}</strong></div><div><small>A* calls</small><strong>{metric.replanning_count}</strong></div><div><small>Expanded nodes</small><strong>{metric.astar_expanded_nodes}</strong></div><div><small>Planning time</small><strong>{metric.planning_time_ms.toFixed(3)} ms</strong></div><div><small>Largest graph</small><strong>{metric.max_graph_nodes} nodes / {metric.max_graph_edges} edges</strong></div>{indoorMode && <><div><small>Observed branches</small><strong>{metric.observed_branches}</strong></div><div><small>Certified free area</small><strong>{metric.observed_free_area?.toFixed(1)} units²</strong></div></>}</div><p className="muted">Turns count heading changes between executed segments. Return bounds apply to recorded local entries, not arbitrary polygonal BARs. Branch IDs are observed exploration anchors, not inferred architectural rooms.</p></section>}
  </main>
}
