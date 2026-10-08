import { useEffect, useState } from 'react'
import { healthCheck } from './api/road'
import { errorText } from './api/client'
import type { Health } from './types/road'
import { RoadPage } from './road/RoadPage'
import { RobotPage } from './robot/RobotPage'
import { BarPage } from './robot/BarPage'
import './App.css'

function App() {
  const [mode, setMode] = useState<'road' | 'robot' | 'bar'>('road')
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  useEffect(() => { healthCheck().then(setHealth).catch(error => setHealthError(errorText(error))) }, [])
  return <div className="app"><header className="app-header"><div className="brand"><span className="brand-mark" aria-hidden="true">✳</span><span>A* <b>Navigation Lab</b></span></div><nav aria-label="Primary"><button type="button" className={mode === 'road' ? 'active' : ''} aria-current={mode === 'road' ? 'page' : undefined} onClick={() => setMode('road')}>Road Navigation</button><button type="button" className={mode === 'robot' ? 'active' : ''} aria-current={mode === 'robot' ? 'page' : undefined} onClick={() => setMode('robot')}>Robot Lab</button><button type="button" className={mode === 'bar' ? 'active' : ''} aria-current={mode === 'bar' ? 'page' : undefined} onClick={() => setMode('bar')}>Blind Alley</button></nav><span className="header-label">A* / DIJKSTRA VISUALIZER</span></header>{mode === 'road' ? <RoadPage health={health} healthError={healthError} /> : mode === 'robot' ? <RobotPage /> : <BarPage />}<footer className="app-footer"><span>Routes and search traces are computed by the C++ engine.</span><span>Road basemap © OpenStreetMap contributors</span></footer></div>
}
export default App
