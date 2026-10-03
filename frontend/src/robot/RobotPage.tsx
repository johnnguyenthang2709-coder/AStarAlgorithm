import { useEffect, useRef, useState } from 'react'
import { gridReplan, gridSearch } from '../api/grid'
import { errorText } from '../api/client'
import type { Algorithm, GridCell } from '../types/common'
import type { GridSearchResponse } from '../types/grid'
import { score } from '../utils/format'
import { SearchMetricsView } from '../components/Metric'
import { PlaybackControls } from '../components/PlaybackControls'
import { AlgorithmInspector } from '../components/AlgorithmInspector'
import { useTracePlayback } from '../hooks/useTracePlayback'
import { RobotGrid } from './RobotGrid'
import { editScenario, initialScenario, sameCell, type Scenario, type Tool } from './scenario'

export function RobotPage() {
  const [scenario, setScenario] = useState<Scenario>(initialScenario)
  const [tool, setTool] = useState<Tool>('obstacle')
  const [movement, setMovement] = useState<4 | 8>(8)
  const [algorithm, setAlgorithm] = useState<Algorithm>('astar')
  const [result, setResult] = useState<GridSearchResponse | null>(null)
  const [robotIndex, setRobotIndex] = useState(0)
  const [robotPlaying, setRobotPlaying] = useState(false)
  const [replanCount, setReplanCount] = useState(0)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const operation = useRef(0)
  const playback = useTracePlayback(result?.trace ?? [])
  const robot = result?.path[robotIndex] ?? scenario.start
  useEffect(() => {
    if (!robotPlaying || !result?.found) return
    const timer = window.setInterval(() => setRobotIndex(previous => {
      const next = Math.min(result.path.length - 1, previous + 1)
      if (next === result.path.length - 1) setRobotPlaying(false)
      return next
    }), 350)
    return () => window.clearInterval(timer)
  }, [robotPlaying, result])
  async function search() {
    if (busy) return
    const requestId = ++operation.current
    playback.pause()
    setBusy('Searching grid…'); setError(''); setNotice(''); setRobotPlaying(false)
    try { const response = await gridSearch({ ...scenario, movement, algorithm, trace: true }); if (operation.current === requestId) { setResult(response); setRobotIndex(0); setReplanCount(0) } } catch (e) { if (operation.current === requestId) setError(errorText(e)) } finally { if (operation.current === requestId) setBusy('') }
  }
  async function replan(cell: GridCell) {
    if (busy) return
    const requestId = ++operation.current
    playback.pause()
    setBusy('Replanning with A*…'); setRobotPlaying(false); setError('')
    try {
      const response = await gridReplan({ grid: scenario.grid, current: robot, goal: scenario.goal, new_obstacles: [cell], movement, algorithm: 'astar', trace: true })
      if (operation.current !== requestId) return
      setScenario(old => editScenario(old, cell, 'obstacle'))
      setResult(response); setRobotIndex(0); setReplanCount(count => count + 1); setAlgorithm('astar')
      setNotice(response.found ? 'Replanned from the robot’s current cell using repeated A*.' : 'Replanned: no path remains from the robot’s current cell.')
    } catch (e) { if (operation.current === requestId) setError(errorText(e)) } finally { if (operation.current === requestId) setBusy('') }
  }
  function edit(cell: GridCell) {
    if (busy) return
    if (tool === 'obstacle' && result?.found && scenario.grid[cell.row][cell.col] === 0 && !sameCell(cell, robot) && !sameCell(cell, scenario.goal) && !sameCell(cell, scenario.start)) { void replan(cell); return }
    const next = editScenario(scenario, cell, tool)
    if (next !== scenario) { operation.current++; playback.restart(); setScenario(next); setResult(null); setRobotPlaying(false); setRobotIndex(0); setNotice('Grid changed. Run a search for the new scenario.') }
  }
  function reset() { operation.current++; playback.restart(); setBusy(''); setScenario(initialScenario()); setResult(null); setRobotIndex(0); setRobotPlaying(false); setReplanCount(0); setNotice(''); setError('') }
  return <main className="page robot-page"><div className="page-top"><div><p className="eyebrow">02 / OCCUPANCY GRID</p><h1>Robot Lab</h1><p>Build a 20 × 30 scenario, inspect search, and replan while the robot moves.</p></div><span className="status-pill">4 / 8 direction movement</span></div>
    <div className="robot-layout"><aside className="control-panel"><div className="panel-title"><h2>Scenario tools</h2><span>Click or drag to edit</span></div><div className="tool-list">{(['start', 'goal', 'obstacle', 'erase'] as Tool[]).map(value => <button type="button" key={value} className={tool === value ? 'tool active' : 'tool'} aria-pressed={tool === value} onClick={() => setTool(value)}><span className={`tool-icon ${value}`}>{value === 'start' ? 'S' : value === 'goal' ? 'G' : value === 'obstacle' ? '■' : '⌫'}</span>{value === 'start' ? 'Set start' : value === 'goal' ? 'Set goal' : value === 'obstacle' ? 'Draw obstacle' : 'Erase'}</button>)}</div>
      <label className="select-field">Algorithm<select value={algorithm} onChange={e => { operation.current++; playback.restart(); setBusy(''); setRobotPlaying(false); setAlgorithm(e.target.value as Algorithm); setResult(null) }}><option value="astar">A* search</option><option value="dijkstra">Dijkstra</option></select></label><label className="select-field">Movement<select value={movement} onChange={e => { operation.current++; playback.restart(); setBusy(''); setRobotPlaying(false); setMovement(Number(e.target.value) as 4 | 8); setResult(null) }}><option value="4">4 directions</option><option value="8">8 directions</option></select></label>
      <button type="button" className="primary full" onClick={search} disabled={!!busy}>Run search</button><button type="button" className="secondary full" onClick={reset}>Reset scenario</button><div className="panel-divider" /><p className="aside-explain">Draw an obstacle after a route appears to trigger repeated A* from the robot’s current cell. Diagonal movement cannot cut blocked corners.</p>
      {busy && <p role="status" className="notice">{busy}</p>}{error && <p role="alert" className="error">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}</aside>
      <div className="robot-workspace"><div className="workspace-bar"><strong>Editable grid</strong><span>Start ({scenario.start.row + 1}, {scenario.start.col + 1}) · Goal ({scenario.goal.row + 1}, {scenario.goal.col + 1})</span></div><RobotGrid scenario={scenario} tool={tool} path={result?.path ?? []} robot={robot} events={result?.trace ?? []} index={playback.index} onEdit={edit} /><p className="grid-keyboard-note">Keyboard: Tab into the grid, move with arrow keys, then press Enter or Space to edit.</p><div className="grid-legend" aria-label="Grid legend"><span><i className="dot start" />Start S</span><span><i className="dot goal" />Goal G</span><span><i className="dot obstacle" />Obstacle</span><span><i className="dot frontier" />Frontier</span><span><i className="dot expanded" />Expanded</span><span><i className="dot path" />Path</span><span><i className="dot robot" />Robot ●</span></div></div></div>
    <div className="results"><section className="result-summary"><div className="section-heading"><h2>Search result</h2><span>{result ? result.found ? 'Path found' : 'No path' : 'Awaiting search'}</span></div>{result ? result.found ? <><div className="hero-metric"><small>Grid path cost</small><strong>{score(result.cost!)}</strong><span>{result.path.length} path cells</span></div><SearchMetricsView metrics={result.metrics} /><div className="simulation-metrics"><span>Robot step <b>{robotIndex + 1} / {result.path.length}</b></span><span>Replans <b>{replanCount}</b></span></div><div className="action-row"><button type="button" onClick={() => setRobotPlaying(!robotPlaying)} disabled={robotIndex >= result.path.length - 1}>{robotPlaying ? 'Pause robot' : 'Run robot'}</button><button type="button" onClick={() => { setRobotIndex(0); setRobotPlaying(false) }}>Restart robot</button></div></> : <p className="empty-note">No path exists through this obstacle layout. Edit the grid and search again.</p> : <p className="empty-note">Edit the grid and run A* or Dijkstra. Algorithm metrics come from C++.</p>}</section>
      <section className="trace-panel"><div className="section-heading"><h2>Grid search playback</h2><span>Backend trace</span></div><p className="muted">Frontier cells are discovered; expanded cells have been processed. The highlighted cell is the current event.</p>{result?.trace.length ? <><PlaybackControls playback={playback} total={result.trace.length} /><AlgorithmInspector event={playback.current} index={playback.index} stateLabel={cell => `(${cell.row + 1}, ${cell.col + 1})`} /></> : <p className="muted">Run a search to enable playback.</p>}</section></div>
  </main>
}
