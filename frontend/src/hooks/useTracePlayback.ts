import { useEffect, useState } from 'react'
const emptyEvents: never[] = []
export function useTracePlayback<T>(events: T[]) {
  const source = events.length ? events : emptyEvents
  const [state, setState] = useState({ source, index: 0, playing: false })
  const [speed, setSpeed] = useState(1)
  // A new trace resets the selection during render, before an old event can paint.
  if (state.source !== source) setState({ source, index: 0, playing: false })
  const index = state.source === source ? state.index : 0
  const playing = state.source === source && state.playing
  useEffect(() => {
    if (!playing || events.length === 0) return
    const timer = window.setInterval(() => setState(previous => {
      if (previous.source !== source) return previous
      const next = Math.min(source.length, previous.index + Math.max(1, Math.round(speed * 5)))
      return { ...previous, index: next, playing: next < source.length }
    }), 80)
    return () => window.clearInterval(timer)
  }, [playing, speed, source, events.length])
  return { index, playing, speed, current: index > 0 ? events[index - 1] : null, play: () => setState(old => ({ ...old, playing: true })), pause: () => setState(old => ({ ...old, playing: false })), step: () => setState(old => ({ ...old, index: Math.min(source.length, old.index + 1) })), restart: () => setState({ source, index: 0, playing: false }), setSpeed }
}
