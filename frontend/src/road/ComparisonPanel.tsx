import type { RoadCompareResponse } from '../types/road'
import { distance, number } from '../utils/format'
export function ComparisonPanel({ result }: { result: RoadCompareResponse }) {
  const rows: [string, number | null, number | null, boolean][] = [
    ['Cost', result.astar.route?.cost_m ?? null, result.dijkstra.route?.cost_m ?? null, true],
    ['Expansions', result.astar.metrics.expanded_nodes, result.dijkstra.metrics.expanded_nodes, false],
    ['Unique expanded', result.astar.metrics.unique_expanded_states, result.dijkstra.metrics.unique_expanded_states, false],
    ['Discovered', result.astar.metrics.unique_discovered_states, result.dijkstra.metrics.unique_discovered_states, false],
    ['Queue pushes', result.astar.metrics.generated_nodes, result.dijkstra.metrics.generated_nodes, false],
  ]
  return <section className="comparison"><div className="section-heading"><h3>A* vs Dijkstra</h3><span>{result.same_optimal_cost ? 'Same optimal cost' : 'Costs differ'}</span></div><table><thead><tr><th>Measure</th><th>A*</th><th>Dijkstra</th></tr></thead><tbody>{rows.map(([label, a, d, meters]) => <tr key={label}><th>{label}</th><td>{a === null ? 'No route' : meters ? distance(a) : number(a)}</td><td>{d === null ? 'No route' : meters ? distance(d) : number(d)}</td></tr>)}</tbody></table><p className="muted">Dijkstra is A* with h(n) = 0. Both use the same directed road graph.</p></section>
}
