import type { GridCell } from '../types/common'
export type Tool = 'start' | 'goal' | 'obstacle' | 'erase'
export type Scenario = { grid: number[][]; start: GridCell; goal: GridCell }
export const sameCell = (a: GridCell, b: GridCell) => a.row === b.row && a.col === b.col
export const cellKey = (cell: GridCell) => `${cell.row},${cell.col}`
export function initialScenario(): Scenario {
  const grid = Array.from({ length: 20 }, () => Array<number>(30).fill(0))
  for (let row = 2; row < 16; row++) if (row !== 9) grid[row][10] = 1
  for (let row = 5; row < 19; row++) if (row !== 13) grid[row][20] = 1
  return { grid, start: { row: 10, col: 2 }, goal: { row: 10, col: 27 } }
}
export function editScenario(scenario: Scenario, cell: GridCell, tool: Tool): Scenario {
  if (tool === 'start' || tool === 'goal') {
    if (tool === 'start' && sameCell(cell, scenario.goal)) return scenario
    if (tool === 'goal' && sameCell(cell, scenario.start)) return scenario
    const grid = scenario.grid.map(row => row.slice()); grid[cell.row][cell.col] = 0
    return { ...scenario, grid, [tool]: cell }
  }
  if (sameCell(cell, scenario.start) || sameCell(cell, scenario.goal)) return scenario
  const value = tool === 'obstacle' ? 1 : 0
  if (scenario.grid[cell.row][cell.col] === value) return scenario
  const grid = scenario.grid.map(row => row.slice()); grid[cell.row][cell.col] = value
  return { ...scenario, grid }
}
