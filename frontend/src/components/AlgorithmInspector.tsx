import type { TraceEvent } from '../types/common'
import { score } from '../utils/format'
export function AlgorithmInspector<T>({ event, index, stateLabel }: { event: TraceEvent<T> | null; index: number; stateLabel: (state: T) => string }) {
  return <section className="inspector" aria-live="polite"><div className="section-heading"><h3>Algorithm inspector</h3><span>f(n) = g(n) + h(n)</span></div>
    {event ? <div className="inspector-grid"><span>Step <b>{index}</b></span><span>Event <b>{event.type}</b></span><span>State <b>{stateLabel(event.state)}</b></span><span>Parent <b>{event.parent === null ? '—' : stateLabel(event.parent)}</b></span><span>g(n) <b>{score(event.g)}</b></span><span>h(n) <b>{score(event.h)}</b></span><span>f(n) <b>{score(event.f)}</b></span></div> : <p className="muted">Play or step through a search to inspect its state.</p>}
  </section>
}
