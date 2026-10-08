import type { ContinuousBarResponse, ContinuousFrame, WorldPoint } from '../types/barContinuous'

export type ContinuousPlaybackState = {
  regions: NonNullable<ContinuousFrame['region']>[]
  edges: NonNullable<ContinuousFrame['obstacle_edges']>
  trail: WorldPoint[]
  path: WorldPoint[]
  entry: WorldPoint[]
  retreat: WorldPoint[]
  target?: WorldPoint
  distance: number
  recoveries: number
  graphPoints: WorldPoint[]
  graphLinks: [number, number][]
  branchId?: number
  branchStatus?: string
}

export function buildContinuousPlayback(result: ContinuousBarResponse): ContinuousPlaybackState[] {
  const regions: ContinuousPlaybackState['regions'] = []
  const edges: ContinuousPlaybackState['edges'] = []
  const trail = [result.start]
  let path: WorldPoint[] = []
  let entry: WorldPoint[] = []
  let retreat: WorldPoint[] = []
  let target: WorldPoint | undefined
  let distance = 0
  let recoveries = 0
  let graphPoints: WorldPoint[] = []
  let graphLinks: [number, number][] = []
  let branchId: number | undefined
  let branchStatus: string | undefined
  return result.frames.map(frame => {
    if (frame.event === 'branch') {
      branchStatus = frame.status
      if (frame.status === 'active') branchId = frame.branch_id
      else branchId = frame.parent_id ?? 0
    }
    if (frame.event === 'recover_start') branchStatus = 'returning to parent'
    if (frame.event === 'sense') {
      if (frame.region) regions.push(frame.region)
      edges.push(...(frame.obstacle_edges ?? []))
    }
    if (frame.event === 'plan') {
      path = frame.path ?? []
      target = frame.target
      entry = []
      retreat = []
      graphPoints = frame.graph_points ?? []
      graphLinks = frame.graph_links ?? []
    }
    if (frame.event === 'recover_start') {
      path = frame.path ?? []
      entry = frame.entry_path ?? []
      retreat = []
      target = frame.anchor
      recoveries++
      graphPoints = frame.graph_points ?? []
      graphLinks = frame.graph_links ?? []
    }
    if (frame.event === 'move') {
      trail.push(frame.position)
      distance += frame.distance ?? 0
      if (frame.phase === 'retreat') retreat.push(frame.position)
    }
    if (frame.event === 'recover_end' || frame.event === 'finish') {
      path = []
      graphPoints = []
      graphLinks = []
    }
    return {
      regions: [...regions], edges: [...edges], trail: [...trail],
      path: [...path], entry: [...entry], retreat: [...retreat], target,
      distance, recoveries, graphPoints, graphLinks,
      branchId, branchStatus,
    }
  })
}

export function interpolatedPose(frames: ContinuousFrame[], playhead: number): { position: WorldPoint; heading: number } {
  const index = Math.max(0, Math.min(frames.length - 1, Math.floor(playhead)))
  const frame = frames[index]
  if (!frame) return { position: { x: 0, y: 0 }, heading: 0 }
  const next = frames[index + 1]
  if (!next || next.event !== 'move') return { position: frame.position, heading: frame.heading }
  const t = Math.max(0, Math.min(1, playhead - index))
  return {
    position: { x: frame.position.x + (next.position.x - frame.position.x) * t,
      y: frame.position.y + (next.position.y - frame.position.y) * t },
    heading: next.heading,
  }
}
