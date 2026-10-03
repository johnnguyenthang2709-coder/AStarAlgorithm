import type { useTracePlayback } from '../hooks/useTracePlayback'
type Playback = ReturnType<typeof useTracePlayback<unknown>>
export function PlaybackControls({ playback, total }: { playback: Playback; total: number }) {
  return <div className="playback" aria-label="Trace playback">
    <button type="button" onClick={playback.playing ? playback.pause : playback.play} disabled={!total || (playback.index === total && !playback.playing)}>{playback.playing ? 'Pause' : 'Play'}</button>
    <button type="button" onClick={playback.step} disabled={playback.index === total}>Step +1</button>
    <button type="button" onClick={playback.restart} disabled={!total}>Restart</button>
    <label>Speed <select value={playback.speed} onChange={e => playback.setSpeed(Number(e.target.value))}><option value="0.2">0.2×</option><option value="1">1×</option><option value="4">4×</option><option value="12">12×</option></select></label>
    <span className="step-count">{playback.index.toLocaleString()} / {total.toLocaleString()} events</span>
  </div>
}
