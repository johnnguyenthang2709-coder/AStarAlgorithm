import { useEffect, useMemo, useState } from 'react'
import { simulateBar } from '../api/bar'
import { errorText } from '../api/client'
import type { BarResponse, BarScenario } from '../types/bar'
import type { GridCell } from '../types/common'
import { cellKey, sameCell } from './scenario'

const options: { value: BarScenario; label: string }[] = [
  { value: 'alley_reachable', label: 'Blind alley · straight' },
    { value: 'alley_turn', label: 'Blind alley · turning branch' },
    { value: 'alley_shortcut', label: 'Blind alley · shorter A* return' },
  { value: 'wide_mouth_alley', label: 'Wide-mouth alley · recovery limit' },
  { value: 'open_route', label: 'Open route' },
  { value: 'unreachable', label: 'Unreachable goal' },
]

function frameState(result: BarResponse, index: number) {
  const known = Array.from({ length: result.rows }, () => Array<number>(result.cols).fill(-1))
  let position = result.start, target: GridCell | null = null, path: GridCell[] = [], entry: GridCell[] = []
  const retreat: GridCell[] = []
  for (const frame of result.frames.slice(0, index + 1)) {
    for (const change of frame.changes) known[change.cell.row][change.cell.col] = change.state
    position = frame.position
    if (frame.event === 'plan') { path = frame.path; target = frame.target }
    if (frame.event === 'recover_start') { path = frame.path; entry = frame.entry_path; target = frame.anchor }
    if (frame.event === 'move' && frame.phase === 'retreat') retreat.push(frame.position)
  }
  return { known, position, target, path: new Set(path.map(cellKey)),
    entry: new Set(entry.map(cellKey)), retreat: new Set(retreat.map(cellKey)) }
}

export function BarPage() {
  const [scenario, setScenario] = useState<BarScenario>('alley_reachable')
  const [radius, setRadius] = useState('2')
  const [result, setResult] = useState<BarResponse | null>(null)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!playing || !result) return
    const timer = window.setInterval(() => setIndex(previous => {
      if (previous >= result.frames.length - 1) { setPlaying(false); return previous }
      return previous + 1
    }), 300)
    return () => window.clearInterval(timer)
  }, [playing, result])
  const state = useMemo(() => result ? frameState(result, index) : null, [result, index])
  async function run() {
    setBusy(true); setError(''); setPlaying(false); setResult(null); setIndex(0)
    try { setResult(await simulateBar(scenario, Math.max(1, Math.min(10, Number(radius) || 1)))) }
    catch (cause) { setError(errorText(cause)) }
    finally { setBusy(false) }
  }
  return <main className="page bar-page">
    <div className="page-top"><div><p className="eyebrow">01 / LIMITED SENSING</p><h1>Blind-Alley Robot Navigation</h1><p>Explore an unknown grid with repeated C++ A* and recover from exhausted branches.</p></div><span className="status-pill">Four-direction · unit cost</span></div>
    <div className="robot-layout"><aside className="control-panel"><div className="panel-title"><h2>Scenario</h2><span>Deterministic benchmark</span></div>
      <label className="select-field">Map<select value={scenario} onChange={event => { setScenario(event.target.value as BarScenario); setResult(null); setPlaying(false) }}>{options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
      <label className="select-field">Sensor radius (cells)<input type="number" min="1" max="10" value={radius} onChange={event => { setRadius(event.target.value); setResult(null); setPlaying(false) }} /></label>
      <button type="button" className="primary full" disabled={busy} onClick={() => void run()}>{busy ? 'Simulating…' : 'Run simulation'}</button>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="panel-divider" /><p className="aside-explain">The robot sees only observed cells. UNKNOWN cells remain unavailable until sensed. The benchmark gate labels recovery after the run; it does not guide the robot.</p>
      {result && <div className="bar-playback"><button type="button" onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => { setPlaying(false); setIndex(Math.min(index + 1, result.frames.length - 1)) }}>Step</button><button type="button" onClick={() => { setPlaying(false); setIndex(0) }}>Restart</button><label>Frame {index + 1} / {result.frames.length}<input aria-label="Playback frame" type="range" min="0" max={result.frames.length - 1} value={index} onChange={event => { setPlaying(false); setIndex(Number(event.target.value)) }} /></label></div>}
    </aside>
      <div className="robot-workspace"><div className="workspace-bar"><strong>Discovered map</strong><span>{result ? `${result.frames[index].event.replace('_', ' ')} · robot (${state!.position.row + 1}, ${state!.position.col + 1})` : 'Run a scenario to reveal cells'}</span></div>
        {result && state ? <div className="grid-viewport"><div className="bar-grid" role="grid" aria-label="Discovered BAR grid" style={{ gridTemplateColumns: `repeat(${result.cols}, minmax(0, 1fr))`, aspectRatio: `${result.cols}/${result.rows}` }}>{state.known.map((row, r) => row.map((value, c) => {
          const cell = { row: r, col: c }, key = cellKey(cell)
          const kind = value === -1 ? 'unknown' : value === 1 ? 'obstacle' : state.retreat.has(key) ? 'retreat' : state.entry.has(key) ? 'entry' : state.path.has(key) ? 'route' : 'free'
          return <div role="gridcell" key={key} className={`bar-cell ${kind} ${sameCell(cell, state.position) ? 'robot-here' : ''}`} aria-label={`Row ${r + 1}, column ${c + 1}: ${value === -1 ? 'unknown' : value === 1 ? 'blocked' : 'free'}${sameCell(cell, state.position) ? ', robot' : ''}`}><span>{sameCell(cell, state.position) ? '●' : sameCell(cell, result.start) && value === 0 ? 'S' : sameCell(cell, result.goal) && value === 0 ? 'G' : state.target && sameCell(cell, state.target) ? '◇' : ''}</span></div>
        }))}</div></div> : <div className="grid-viewport"><p className="empty-note">The environment is initially unknown to the robot.</p></div>}
        <div className="grid-legend"><span><i className="dot bar-unknown" />Unknown</span><span><i className="dot obstacle" />Observed obstacle</span><span><i className="dot path" />A* path</span><span><i className="dot bar-entry" />Entry</span><span><i className="dot bar-retreat" />Retreat</span><span><i className="dot robot" />Robot</span></div>
      </div></div>
    {result && index < result.frames.length - 1 && <p className="muted">Continue playback to see the episode outcome and benchmark evaluation.</p>}
    {result && index === result.frames.length - 1 && <section className="bar-summary">
      <div className="section-heading"><h2>Episode result</h2><span>{result.status.replaceAll('_', ' ')}</span></div>
      <p className="notice">BAR evaluation: {result.metrics.bar_evaluation_status.replaceAll('_', ' ')}. {result.metrics.bar_evaluation_status === 'uncertified_exit' ? 'The robot left the benchmark alley, but no locked retreat was executed.' : 'Gate labels are computed after navigation.'}</p>
      <div className="bar-metrics">
        <div><small>Goal</small><strong>{result.success ? 'Reached' : 'Not reached'}</strong></div>
        <div><small>Executed distance</small><strong>{result.metrics.executed_distance} cells</strong></div>
        <div><small>Gate entry / retreat</small><strong>{result.metrics.gate_entry_length ?? '—'} / {result.metrics.gate_retreat_length ?? '—'}</strong></div>
        <div><small>Retreat ratio</small><strong>{result.metrics.gate_retreat_ratio?.toFixed(2) ?? '—'}</strong></div>
        <div><small>A* expanded nodes</small><strong>{result.metrics.astar_expanded_nodes}</strong></div>
        <div><small>A* calls</small><strong>{result.metrics.replanning_count}</strong></div>
        <div><small>Planning time</small><strong>{result.metrics.planning_time_ms.toFixed(3)} ms</strong></div>
        <div><small>Turns</small><strong>{result.metrics.turn_count}</strong></div>
      </div>
      <p className="muted">A turn is a change between consecutive four-direction movement headings. Gate metrics are post-hoc evaluation labels.</p>
    </section>}
  </main>
}
