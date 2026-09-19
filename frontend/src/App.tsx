import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './lib/api'
import { useAsync } from './lib/hooks'
import { ICONS, NAV, type ViewId } from './lib/nav'
import type { SimulationSummary } from './lib/types'
import Home from './views/Home'
import Projects from './views/Projects'
import Simulations from './views/Simulations'
import Workspace from './views/Workspace'
import Comparison from './views/Comparison'
import Validation from './views/Validation'
import Diagnostics from './views/Diagnostics'
import Assistant from './views/Assistant'
import Optimization from './views/Optimization'
import Reports from './views/Reports'
import DataFiles from './views/DataFiles'
import Settings from './views/Settings'

export interface AppContext {
  simulations: SimulationSummary[]
  active: SimulationSummary | null
  setActive: (id: string) => void
  go: (view: ViewId, simulationId?: string) => void
  toast: (message: string) => void
  filterRequest: { field: string; fraction: number; nonce: number } | null
}

function icon(name: string, size = 14) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor"
         strokeWidth={1.3} strokeLinejoin="round" strokeLinecap="round">
      <path d={ICONS[name] ?? ICONS.home} />
    </svg>
  )
}

export default function App() {
  const [view, setView] = useState<ViewId>('home')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [filterRequest, setFilterRequest] = useState<AppContext['filterRequest']>(null)

  const sims = useAsync(() => api.simulations(), [])
  const health = useAsync(() => api.health(), [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    if (!activeId && sims.data?.length) setActiveId(sims.data[0].id)
  }, [sims.data, activeId])

  const toast = useCallback((message: string) => {
    setToastMsg(message)
    window.setTimeout(() => setToastMsg(null), 2400)
  }, [])

  const active = useMemo(
    () => sims.data?.find((s) => s.id === activeId) ?? null,
    [sims.data, activeId],
  )

  const ctx: AppContext = {
    simulations: sims.data ?? [],
    active,
    setActive: setActiveId,
    go: (v, id) => { if (id) setActiveId(id); setView(v) },
    toast,
    filterRequest,
  }

  const views: Record<ViewId, JSX.Element> = {
    home: <Home ctx={ctx} />,
    projects: <Projects ctx={ctx} />,
    simulations: <Simulations ctx={ctx} />,
    fea: <Workspace ctx={ctx} domain="FEA" />,
    cfd: <Workspace ctx={ctx} domain="CFD" />,
    thermal: <Workspace ctx={ctx} domain="Thermal" />,
    mbd: <Workspace ctx={ctx} domain="MBD" />,
    multiphysics: <Optimization ctx={ctx} modulesOnly />,
    comparison: <Comparison ctx={ctx} />,
    validation: <Validation ctx={ctx} />,
    diagnostics: <Diagnostics ctx={ctx} />,
    assistant: <Assistant ctx={ctx} onFilter={(field, fraction) => {
      setFilterRequest({ field, fraction, nonce: Date.now() })
    }} />,
    optimization: <Optimization ctx={ctx} />,
    reports: <Reports ctx={ctx} />,
    data: <DataFiles ctx={ctx} onImported={() => sims.reload()} />,
    settings: <Settings ctx={ctx} theme={theme} onTheme={setTheme} />,
  }

  return (
    <div className="app">
      <header className="cmdbar">
        <div className="brand">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5">
            <path d="M12 2.5 21 7v10l-9 4.5L3 17V7Z" />
            <path d="M3 7l9 4.5L21 7M12 11.5V21.5" strokeOpacity=".5" />
          </svg>
          <div>
            <b>CAE Results Analyzer</b><br />
            <span>post-processing · v{health.data?.version ?? '—'}</span>
          </div>
        </div>
        <div className="cmd-actions">
          <button className="cmd" onClick={() => setView('data')}>Import result</button>
          <button className="cmd" onClick={() => setView('projects')}>Projects</button>
          <button className="cmd" onClick={() => setView('comparison')}>Compare</button>
          <button className="cmd" onClick={() => setView('validation')}>Validation</button>
          <button className="cmd" onClick={() => setView('reports')}>Generate report</button>
        </div>
        <div className="cmd-right">
          <div className="ctx">
            <span className="dot" />
            <b>{active ? active.name : 'No simulation selected'}</b>
            <i>{active ? `${active.id} · ${active.domain}` : ''}</i>
          </div>
          <button className="iconbtn" title="Switch theme"
                  onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {icon('set', 16)}
          </button>
          <button className="iconbtn" title="Collapse sidebar" onClick={() => setCollapsed(!collapsed)}>
            {icon('sim', 16)}
          </button>
        </div>
      </header>

      <div className={`shell${collapsed ? ' collapsed' : ''}`}>
        <nav className="rail">
          {NAV.map((entry, i) =>
            'group' in entry ? (
              <div className="rail-group" key={`g${i}`}>{entry.group}</div>
            ) : (
              <button key={entry.id} className={`navitem${view === entry.id ? ' on' : ''}`}
                      onClick={() => {
                        if (entry.domain) {
                          const match = (sims.data ?? []).find((s) => s.domain === entry.domain)
                          if (match) setActiveId(match.id)
                        }
                        setView(entry.id)
                      }}>
                {icon(entry.icon)}<span>{entry.label}</span>
              </button>
            ),
          )}
        </nav>
        <main style={{ minWidth: 0, overflow: 'hidden' }}>
          <div className="view on">{views[view]}</div>
        </main>
      </div>

      <footer className="status">
        <span>{active ? active.solver : '—'}</span>
        <div className="sep" />
        <span>{active ? `Units: ${Object.values(active.units).join(' · ')}` : 'Units: —'}</span>
        <div className="sep" />
        <span>{sims.error ? `API error: ${sims.error}` : `${sims.data?.length ?? 0} simulations loaded`}</span>
        <div className="r">
          <span>{active ? `${active.nodes.toLocaleString()} nodes` : ''}</span>
          <span>Sample data · not for design release</span>
        </div>
      </footer>

      <div className={`toast${toastMsg ? ' on' : ''}`}>{toastMsg}</div>
    </div>
  )
}
