import type { BarResponse } from '../types/bar'
import type { GridCell } from '../types/common'

export type BarPlaybackState = {
  known: Int8Array
  position: GridCell
  target: GridCell | null
  path: ReadonlySet<number>
  entry: ReadonlySet<number>
  retreat: ReadonlySet<number>
  observed: number
  moves: number
}

export function barCellIndex(cell: GridCell, cols: number): number {
  return cell.row * cols + cell.col
}

/** Cache observed-map snapshots once so seeking does not replay every earlier frame. */
export function buildBarPlayback(result: BarResponse): BarPlaybackState[] {
  let known = new Int8Array(result.rows * result.cols).fill(-1)
  let position = result.start
  let target: GridCell | null = null
  let path: ReadonlySet<number> = new Set<number>()
  let entry: ReadonlySet<number> = new Set<number>()
  let retreat: ReadonlySet<number> = new Set<number>()
  let observed = 0
  let moves = 0
  return result.frames.map(frame => {
    known = known.slice()
    for (const change of frame.changes) {
      const index = barCellIndex(change.cell, result.cols)
      if (known[index] === -1) observed++
      known[index] = change.state
    }
    position = frame.position
    if (frame.event === 'plan') {
      target = frame.target
      path = new Set(frame.path.map(cell => barCellIndex(cell, result.cols)))
      entry = new Set()
    } else if (frame.event === 'recover_start') {
      target = frame.anchor
      path = new Set(frame.path.map(cell => barCellIndex(cell, result.cols)))
      entry = new Set(frame.entry_path.map(cell => barCellIndex(cell, result.cols)))
    } else if (frame.event === 'move') {
      moves++
      if (frame.phase === 'retreat') {
        const nextRetreat = new Set(retreat)
        nextRetreat.add(barCellIndex(frame.position, result.cols))
        retreat = nextRetreat
      }
    }
    return { known, position, target, path, entry, retreat, observed, moves }
  })
}

export function observedFrontiers(known: Int8Array, rows: number, cols: number): ReadonlySet<number> {
  const frontiers = new Set<number>()
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const index = row * cols + col
      if (known[index] !== 0) continue
      if ((row > 0 && known[index - cols] === -1) ||
          (row + 1 < rows && known[index + cols] === -1) ||
          (col > 0 && known[index - 1] === -1) ||
          (col + 1 < cols && known[index + 1] === -1)) {
        frontiers.add(index)
      }
    }
  }
  return frontiers
}
