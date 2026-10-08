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
  return result.frames.map(frame => {
    if (frame.event === 'sense') {
      if (frame.region) regions.push(frame.region)
      edges.push(...(frame.obstacle_edges ?? []))
    }
    if (frame.event === 'plan') {
      path = frame.path ?? []
      target = frame.target
      entry = []
      retreat = []
    }
    if (frame.event === 'recover_start') {
      path = frame.path ?? []
      entry = frame.entry_path ?? []
      retreat = []
      target = frame.anchor
      recoveries++
    }
    if (frame.event === 'move') {
      trail.push(frame.position)
      distance += frame.distance ?? 0
      if (frame.phase === 'retreat') retreat.push(frame.position)
    }
    if (frame.event === 'recover_end') path = []
    return {
      regions: [...regions], edges: [...edges], trail: [...trail],
      path: [...path], entry: [...entry], retreat: [...retreat], target,
      distance, recoveries,
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
