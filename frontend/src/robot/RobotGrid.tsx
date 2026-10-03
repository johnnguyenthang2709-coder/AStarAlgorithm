import { useMemo, useRef, useState } from 'react'
import type { GridCell, TraceEvent } from '../types/common'
import type { Scenario, Tool } from './scenario'
import { cellKey, sameCell } from './scenario'
import { applyTraceState } from '../utils/traceState'
export function RobotGrid({ scenario, tool, path, robot, events, index, onEdit }: { scenario: Scenario; tool: Tool; path: GridCell[]; robot: GridCell; events: TraceEvent<GridCell>[]; index: number; onEdit: (cell: GridCell) => void }) {
  const [dragging, setDragging] = useState(false)
  const [focusedCell, setFocusedCell] = useState(() => cellKey(scenario.start))
  const cellButtons = useRef(new Map<string, HTMLButtonElement>())
  function moveFocus(cell: GridCell, key: string) {
    const delta = key === 'ArrowUp' ? [-1, 0] : key === 'ArrowDown' ? [1, 0] : key === 'ArrowLeft' ? [0, -1] : key === 'ArrowRight' ? [0, 1] : null
    if (!delta) return false
    const next = { row: Math.max(0, Math.min(scenario.grid.length - 1, cell.row + delta[0])), col: Math.max(0, Math.min(scenario.grid[0].length - 1, cell.col + delta[1])) }
    const target = cellKey(next)
    setFocusedCell(target); cellButtons.current.get(target)?.focus()
    return true
  }
  const state = useMemo(() => {
    const frontier = new Set<string>(), expanded = new Set<string>()
    for (let i = 0; i < index; i++) {
      const event = events[i], key = cellKey(event.state)
      applyTraceState(frontier, expanded, event, key)
    }
    return { frontier, expanded, current: index ? cellKey(events[index - 1].state) : '' }
  }, [events, index])
  const route = useMemo(() => new Set(path.map(cellKey)), [path])
  return <div className="grid-viewport"><div className="robot-grid" role="grid" aria-label="Editable robot grid" style={{ gridTemplateColumns: `repeat(${scenario.grid[0].length}, minmax(0, 1fr))` }} onPointerUp={() => setDragging(false)} onPointerLeave={() => setDragging(false)}>
    {scenario.grid.map((row, r) => row.map((value, c) => {
      const cell = { row: r, col: c }, key = cellKey(cell)
      const start = sameCell(cell, scenario.start), goal = sameCell(cell, scenario.goal), robotHere = sameCell(cell, robot)
      const kind = value ? 'obstacle' : start ? 'start' : goal ? 'goal' : state.current === key ? 'current' : route.has(key) ? 'route' : state.expanded.has(key) ? 'expanded' : state.frontier.has(key) ? 'frontier' : 'free'
      return <button type="button" role="gridcell" key={key} ref={element => { if (element) cellButtons.current.set(key, element); else cellButtons.current.delete(key) }} tabIndex={focusedCell === key ? 0 : -1} className={`grid-cell ${kind} ${robotHere ? 'robot-here' : ''}`} aria-label={`Row ${r + 1}, column ${c + 1}: ${robotHere ? 'robot, ' : ''}${kind}`} onFocus={() => setFocusedCell(key)} onKeyDown={e => { if (moveFocus(cell, e.key)) e.preventDefault() }} onPointerDown={e => { if (e.pointerType !== 'mouse' || e.button === 0) { setDragging(true); onEdit(cell) } }} onPointerEnter={() => { if (dragging && (tool === 'obstacle' || tool === 'erase')) onEdit(cell) }} onClick={e => { if (e.detail === 0) onEdit(cell) }}><span aria-hidden="true">{robotHere ? '●' : start ? 'S' : goal ? 'G' : ''}</span></button>
    }))}</div></div>
}
