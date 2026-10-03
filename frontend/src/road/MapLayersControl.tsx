import type { Layers } from './cartography'
export function MapLayersControl({ layers, buildingsAvailable, onToggle }: { layers: Layers; buildingsAvailable: boolean; onToggle: (key: keyof Layers) => void }) {
  const groups: [string, [keyof Layers, string][]][] = [
    ['Map', [['streets', 'Street names'], ...(buildingsAvailable ? [['buildings', 'Buildings'] as [keyof Layers, string]] : []), ['landmarks', 'Landmarks']]],
    ['Algorithm', [['search', 'Search states'], ['arrows', 'One-way arrows'], ['nodes', 'Graph nodes']]],
  ]
  return <details className="map-layers"><summary>Map layers</summary><div className="map-layers-body">{groups.map(([group, entries]) => <fieldset key={group}><legend>{group}</legend>{entries.map(([key, label]) => <label key={key}><input type="checkbox" checked={layers[key]} onChange={() => onToggle(key)} />{label}</label>)}</fieldset>)}</div></details>
}
