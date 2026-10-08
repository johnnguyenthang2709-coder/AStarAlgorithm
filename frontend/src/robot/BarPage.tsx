import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { simulateBar } from '../api/bar'
import { errorText } from '../api/client'
import type { BarFrame, BarResponse, BarScenario } from '../types/bar'
import type { GridCell } from '../types/common'
import { sameCell } from './scenario'
import { buildBarPlayback, observedFrontiers } from './barPlayback'

const options: { value: BarScenario; label: string; description: string }[] = [
  { value: 'expedition_narrow', label: '32 × 32 · Branching chamber', description: 'A single entrance leads into a chamber with loops, obstacle islands, and nested dead ends. The known bridge can certify a return.' },
  { value: 'expedition_wide', label: '40 × 40 · Wide entrance', description: 'A three-cell mouth leads into a larger obstacle field. Interior branches may recover, while the overall alley exit remains uncertified.' },
  { value: 'alley_reachable', label: '7 × 15 · Straight alley', description: 'Original short certified recovery benchmark.' },
  { value: 'alley_turn', label: '11 × 17 · Turning branch', description: 'Original turning branch benchmark.' },
  { value: 'alley_shortcut', label: '7 × 15 · Shorter A* return', description: 'The A* retreat can be shorter than the actual entry trail.' },
  { value: 'wide_mouth_alley', label: '9 × 15 · Recovery limit', description: 'Original wide-mouth counterexample with an uncertified exit.' },
  { value: 'open_route', label: '3 × 9 · Open route', description: 'A route without a blind alley.' },
  { value: 'unreachable', label: '3 × 7 · Unreachable goal', description: 'Exploration ends after every reachable informative frontier is exhausted.' },
]

function coordinates(cell: GridCell | null): string {
  return cell ? `row ${cell.row + 1}, column ${cell.col + 1}` : 'the selected frontier'
}

function describeFrame(frame: BarFrame): { title: string; detail: string } {
  switch (frame.event) {
    case 'sense':
      return { title: 'Sensing nearby cells', detail: `${frame.changes.length} new cells observed. Obstacles hide cells behind them.` }
    case 'plan':
      return { title: 'A* replans on the discovered map', detail: `Next target: ${coordinates(frame.target)}. Unknown cells remain unavailable.` }
    case 'move':
      return frame.phase === 'retreat'
        ? { title: 'Executing locked retreat', detail: 'The robot follows the complete return path while new sensing continues.' }
        : { title: 'Exploring one step', detail: 'The robot moves on an observed free cell, then senses again.' }
    case 'recover_start':
      return { title: frame.fallback ? 'Reversing recorded entry' : 'A* computes the return', detail: `Recognized exhausted branch. Entry ${frame.entry_path.length - 1} cells; selected return ${frame.path.length - 1} cells.` }
    case 'recover_end':
      return { title: 'Retreat completed', detail: `Executed ${frame.retreat_length} cells against a recorded entry of ${frame.entry_length}.` }
    case 'finish':
      return { title: frame.status === 'goal_reached' ? 'Goal reached' : 'Exploration ended', detail: frame.status === 'goal_reached' ? 'The destination has been reached.' : 'No reachable informative frontier remains.' }
  }
}

export function BarPage() {
  const [scenario, setScenario] = useState<BarScenario>('expedition_narrow')
  const [radius, setRadius] = useState('2')
  const [result, setResult] = useState<BarResponse | null>(null)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(2)
  const [zoom, setZoom] = useState(1)
  const [showFrontiers, setShowFrontiers] = useState(true)
  const [followRobot, setFollowRobot] = useState(true)
  const [viewport, setViewport] = useState({ width: 900, height: 690 })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const viewportRef = useRef<HTMLDivElement>(null)

  const timeline = useMemo(() => result ? buildBarPlayback(result) : [], [result])
  const state = timeline[index]
  const frame = result?.frames[index]
  const frontiers = useMemo(() => result && state
    ? observedFrontiers(state.known, result.rows, result.cols)
    : new Set<number>(), [result, state])
  const description = frame ? describeFrame(frame) : null
  const scenarioInfo = options.find(option => option.value === scenario)!

  useEffect(() => {
    const node = viewportRef.current
    if (!node || typeof ResizeObserver === 'undefined') return
    const update = () => {
      if (node.clientWidth > 0 && node.clientHeight > 0) {
        setViewport({ width: node.clientWidth, height: node.clientHeight })
      }
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(node)
    return () => observer.disconnect()
  }, [result])

  useEffect(() => {
    if (!playing || !result) return
    const timer = window.setInterval(() => setIndex(previous => {
      if (previous >= result.frames.length - 1) {
        setPlaying(false)
        return previous
      }
      return previous + 1
    }), 240 / speed)
    return () => window.clearInterval(timer)
  }, [playing, result, speed])

  useEffect(() => {
    const stage = viewportRef.current
    const robot = stage?.querySelector('.bar-cell.robot-here')
    if (!followRobot || !stage || !robot || stage.clientWidth === 0) return
    const stageRect = stage.getBoundingClientRect()
    const robotRect = robot.getBoundingClientRect()
    stage.scrollLeft += robotRect.left + robotRect.width / 2 - stageRect.left - stage.clientWidth / 2
    stage.scrollTop += robotRect.top + robotRect.height / 2 - stageRect.top - stage.clientHeight / 2
  }, [followRobot, index, result, zoom, viewport])

  async function run() {
    setBusy(true)
    setError('')
    setPlaying(false)
    setResult(null)
    setIndex(0)
    setZoom(1)
    try {
      const episode = await simulateBar(scenario, Math.max(1, Math.min(10, Number(radius) || 1)))
      setResult(episode)
      setZoom(episode.rows >= 30 ? 1.25 : 1)
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setBusy(false)
    }
  }

  const fitCell = result ? Math.min(42, Math.max(14, Math.floor(Math.min(
    (viewport.width - 34 - result.cols) / result.cols,
    (viewport.height - 34 - result.rows) / result.rows,
  )))) : 24
  const cellSize = Math.round(fitCell * zoom)
  const gridStyle = { '--bar-cell-size': `${cellSize}px`, gridTemplateColumns: `repeat(${result?.cols ?? 1}, var(--bar-cell-size))` } as CSSProperties
  const nextRecovery = result?.frames.findIndex((item, frameIndex) => frameIndex > index && item.event === 'recover_start') ?? -1

  return <main className="page bar-page">
    <div className="page-top"><div><p className="eyebrow">01 / LIMITED SENSING</p><h1>Blind-Alley Robot Navigation</h1><p>Watch a robot reveal an unknown world, plan with C++ A*, and recover from exhausted branches.</p></div><span className="status-pill">Four directions · unit cost</span></div>
    <div className="robot-layout bar-layout">
      <aside className="control-panel bar-control">
        <div className="panel-title"><h2>Mission setup</h2><span>Deterministic maps</span></div>
        <label className="select-field">Map<select value={scenario} onChange={event => { setScenario(event.target.value as BarScenario); setResult(null); setPlaying(false); setZoom(1) }}>{options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <p className="bar-scenario-description">{scenarioInfo.description}</p>
        <label className="select-field">Sensor radius (cells)<input type="number" min="1" max="10" value={radius} onChange={event => { setRadius(event.target.value); setResult(null); setPlaying(false) }} /></label>
        <button type="button" className="primary full" disabled={busy} onClick={() => void run()}>{busy ? 'Simulating…' : 'Run simulation'}</button>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="panel-divider" />
        <p className="aside-explain">Only sensed cells enter the planner. The benchmark gate labels crossings after the episode; it never guides exploration or retreat.</p>
        <div className="bar-control-note"><strong>How to read the map</strong><span>Outlined free cells are frontiers beside unknown space. Amber records a recognized branch entry; green shows the executed return.</span></div>
      </aside>
      <section className="robot-workspace bar-workspace" aria-label="Robot simulation">
        <div className="workspace-bar"><strong>Discovered map</strong><span>{result ? `${result.rows} × ${result.cols} cells · ${scenarioInfo.label.split(' · ')[1]}` : 'World initially unknown'}</span></div>
        {result && state && frame && description && <div className="bar-live-status">
          <div className="bar-event" data-event={frame.event}><small>{frame.event.replace('_', ' ')}</small><strong>{description.title}</strong><span>{description.detail}</span></div>
          <div className="bar-live-counts"><div><small>Observed</small><strong>{state.observed} / {result.rows * result.cols}</strong></div><div><small>Frontiers</small><strong>{frontiers.size}</strong></div><div><small>Moves</small><strong>{state.moves}</strong></div><div><small>Position</small><strong>{state.position.row + 1}, {state.position.col + 1}</strong></div></div>
        </div>}
        <div className="bar-map-stage" ref={viewportRef}>
          {result && state ? <div className="bar-grid" role="grid" aria-label="Discovered BAR grid" style={gridStyle}>
            {Array.from({ length: result.rows * result.cols }, (_, cellIndex) => {
              const row = Math.floor(cellIndex / result.cols)
              const col = cellIndex % result.cols
              const cell = { row, col }
              const value = state.known[cellIndex]
              const isRobot = sameCell(cell, state.position)
              const isGoal = sameCell(cell, result.goal)
              const isStart = sameCell(cell, result.start)
              const isTarget = state.target && sameCell(cell, state.target)
              const isFrontier = showFrontiers && frontiers.has(cellIndex) && !isRobot && !isGoal
              const kind = value === -1 ? 'unknown' : value === 1 ? 'obstacle' : state.retreat.has(cellIndex) ? 'retreat' : state.entry.has(cellIndex) ? 'entry' : state.path.has(cellIndex) ? 'route' : 'free'
              const marker = isRobot ? '●' : isGoal ? 'G' : isStart && value === 0 ? 'S' : isTarget && value === 0 ? '◇' : ''
              return <div role="gridcell" key={cellIndex} className={`bar-cell ${kind}${isRobot ? ' robot-here' : ''}${isGoal ? ' goal-cell' : ''}${isFrontier ? ' frontier-cell' : ''}`} aria-label={`Row ${row + 1}, column ${col + 1}: ${value === -1 ? 'unknown' : value === 1 ? 'blocked' : 'free'}${isRobot ? ', robot' : ''}${isGoal ? ', goal' : ''}${isFrontier ? ', frontier' : ''}`}><span>{marker}</span></div>
            })}
          </div> : <div className="bar-empty"><strong>Ready to explore</strong><span>Choose a map and run the simulation. The robot will reveal only what it can sense.</span></div>}
        </div>
        <div className="bar-map-tools"><div className="bar-zoom"><span>View</span><button type="button" aria-label="Zoom out" disabled={!result || zoom <= 1} onClick={() => setZoom(value => Math.max(1, value - 0.25))}>−</button><button type="button" disabled={!result} onClick={() => setZoom(1)}>Fit</button><button type="button" aria-label="Zoom in" disabled={!result || zoom >= 2} onClick={() => setZoom(value => Math.min(2, value + 0.25))}>+</button><small>{Math.round(zoom * 100)}%</small></div><label className="bar-frontier-toggle"><input type="checkbox" checked={showFrontiers} onChange={event => setShowFrontiers(event.target.checked)} /> Show frontiers</label><label className="bar-frontier-toggle"><input type="checkbox" checked={followRobot} onChange={event => setFollowRobot(event.target.checked)} /> Follow robot</label><span className="bar-pan-hint">Turn off follow to pan freely</span></div>
        {result && <div className="bar-playback"><div className="bar-playback-buttons"><button type="button" onClick={() => { if (index >= result.frames.length - 1) setIndex(0); setPlaying(value => !value) }}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => { setPlaying(false); setIndex(value => Math.min(value + 1, result.frames.length - 1)) }}>Step</button><button type="button" onClick={() => { setPlaying(false); setIndex(0) }}>Restart</button><button type="button" disabled={nextRecovery < 0} onClick={() => { setPlaying(false); setIndex(nextRecovery) }}>Next recovery</button></div><label className="bar-speed">Speed<select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value={1}>Careful</option><option value={2}>Normal</option><option value={4}>Fast</option></select></label><label className="bar-scrubber">Frame {index + 1} / {result.frames.length}<input aria-label="Playback frame" type="range" min="0" max={result.frames.length - 1} value={index} onChange={event => { setPlaying(false); setIndex(Number(event.target.value)) }} /></label></div>}
        <div className="grid-legend bar-legend"><span><i className="dot bar-unknown" />Unknown</span><span><i className="dot bar-free" />Observed free</span><span><i className="dot obstacle" />Observed obstacle</span><span><i className="dot bar-frontier" />Frontier</span><span><i className="dot path" />Selected path</span><span><i className="dot bar-entry" />Entry</span><span><i className="dot bar-retreat" />Retreat</span><span><i className="dot robot" />Robot / goal</span></div>
      </section>
    </div>
    {result && index < result.frames.length - 1 && <p className="muted bar-outcome-note">Continue playback to see the outcome and benchmark evaluation. Use “Next recovery” to jump to a recognized branch.</p>}
    {result && index === result.frames.length - 1 && <section className="bar-summary">
      <div className="section-heading"><h2>Episode result</h2><span>{result.status.replaceAll('_', ' ')}</span></div>
      <p className="notice">BAR evaluation: {result.metrics.bar_evaluation_status.replaceAll('_', ' ')}. {result.metrics.bar_evaluation_status === 'uncertified_exit' ? 'The robot exited the benchmark alley without a locked retreat across its gate; smaller interior branches may still have recovered.' : 'Gate labels are computed after navigation.'}</p>
      <div className="bar-metrics"><div><small>Goal</small><strong>{result.success ? 'Reached' : 'Not reached'}</strong></div><div><small>Executed distance</small><strong>{result.metrics.executed_distance} cells</strong></div><div><small>Gate entry / retreat</small><strong>{result.metrics.gate_entry_length ?? '—'} / {result.metrics.gate_retreat_length ?? '—'}</strong></div><div><small>Retreat ratio</small><strong>{result.metrics.gate_retreat_ratio?.toFixed(2) ?? '—'}</strong></div><div><small>A* expanded nodes</small><strong>{result.metrics.astar_expanded_nodes}</strong></div><div><small>A* calls</small><strong>{result.metrics.replanning_count}</strong></div><div><small>Planning time</small><strong>{result.metrics.planning_time_ms.toFixed(3)} ms</strong></div><div><small>Turns</small><strong>{result.metrics.turn_count}</strong></div></div>
      <p className="muted">A turn changes the heading between consecutive cardinal moves. Gate metrics are evaluation labels, not robot knowledge.</p>
    </section>}
  </main>
}
