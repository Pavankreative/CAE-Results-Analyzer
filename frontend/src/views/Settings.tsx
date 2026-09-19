import type { AppContext } from '../App'
import { Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

export default function Settings({ ctx, theme, onTheme }:
  { ctx: AppContext; theme: 'dark' | 'light'; onTheme: (t: 'dark' | 'light') => void }) {
  const health = useAsync(() => api.health(), [])

  return (
    <div className="scroll">
      <div className="vhead"><h1>Settings</h1><p>Appearance and backend connection.</p></div>
      <div className="sub">Units are a property of each imported result set and are not overridden here.</div>

      <div className="grid g2">
        <Slab title="Appearance">
          <div className="body">
            <div className="ctl">
              <label>Theme</label>
              <select value={theme} onChange={(e) => onTheme(e.target.value as 'dark' | 'light')}>
                <option value="dark">Dark (default)</option>
                <option value="light">Light</option>
              </select>
            </div>
            <p className="hint">
              Chrome colours stay neutral in both themes so scientific colour maps are read accurately.
            </p>
          </div>
        </Slab>

        <Slab title="Backend">
          {health.loading && <Loading what="the backend status" />}
          {health.error && (
            <div className="body">
              <p style={{ color: 'var(--crit)', fontSize: 12.5 }}>{health.error}</p>
              <p className="hint">Start it with <code>uvicorn app.main:app --reload</code> from <code>backend/</code>.</p>
            </div>
          )}
          {health.data && (
            <table className="data">
              <tbody>
                <tr><td style={{ color: 'var(--ink-3)' }}>Status</td><td className="n">{health.data.status}</td></tr>
                <tr><td style={{ color: 'var(--ink-3)' }}>Version</td><td className="n">{health.data.version}</td></tr>
                <tr><td style={{ color: 'var(--ink-3)' }}>Simulations</td><td className="n">{health.data.simulations}</td></tr>
                <tr><td style={{ color: 'var(--ink-3)' }}>Loaded in this session</td><td className="n">{ctx.simulations.length}</td></tr>
              </tbody>
            </table>
          )}
        </Slab>
      </div>
    </div>
  )
}
