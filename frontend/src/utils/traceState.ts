import type { TraceEvent } from '../types/common'

export function tracePhase(type: TraceEvent<unknown>['type']): 'frontier' | 'expanded' | null {
  if (type === 'DISCOVER' || type === 'UPDATE') return 'frontier'
  if (type === 'EXPAND' || type === 'GOAL_FOUND') return 'expanded'
  return null
}

export function applyTraceState<T>(frontier: Set<string>, expanded: Set<string>, event: TraceEvent<T>, key: string): void {
  const phase = tracePhase(event.type)
  if (phase === 'frontier') { expanded.delete(key); frontier.add(key) }
  if (phase === 'expanded') { frontier.delete(key); expanded.add(key) }
}
