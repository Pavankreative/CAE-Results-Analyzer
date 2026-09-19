import type { AppContext } from '../App'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { DOMAIN_VIEW } from '../lib/nav'
import { ErrorNote, Loading, Slab, StatusPill } from '../components/Primitives'

export default function Home({ ctx }: { ctx: AppContext }) {
  const overview = useAsync(async () => {
    const sims = await api.simulations()
    const rows = await Promise.all(sims.map(async (s) => ({
      sim: s,
      validation: await api.validation(s.id),
      diagnostics: await api.diagnostics(s.id),
    })))
    return { rows, projects: await api.projects() }
  }, [])

  if (overview.error) return <ErrorNote error={overview.error} />
  if (!overview.data) return <Loading what="the workspace" />

  const { rows, projects } = overview.data
  const critical = rows.reduce((a, r) => a + r.diagnostics.counts.critical, 0)
  const warnings = rows.reduce((a, r) => a + r.diagnostics.counts.warning, 0)

  return (
    <div className="scroll">
      <div className="vhead">
        <h1>Workspace</h1>
        <p>Every value in this build comes from the loaded result model. The bundled datasets are
          labelled as sample data.</p>
      </div>
      <div className="sub">{rows.length} simulations · {projects.length} projects · solver-independent result model</div>

      <div className="grid g4" style={{ marginBottom: 16 }}>
        {[
          ['Projects', projects.length, 'one per imported dataset'],
          ['Simulations', rows.length, `${rows.reduce((a, r) => a + r.sim.fields.length, 0)} result fields`],
          ['Open findings', critical + warnings, `${critical} critical · ${warnings} warnings`],
          ['Nodes analysed', rows.reduce((a, r) => a + r.sim.nodes, 0).toLocaleString(), 'across all loaded meshes'],
        ].map(([k, v, d]) => (
          <div className="slab stat" key={String(k)}>
            <span className="k">{k}</span><span className="v">{v}</span><span className="d">{d}</span>
          </div>
        ))}
      </div>

      <div className="qa" style={{ marginBottom: 18 }}>
        {[
          ['Open a workspace', 'Tree, viewport and analysis panels', () => ctx.go('simulations')],
          ['Import a result', 'VTK legacy, CSV or native JSON', () => ctx.go('data')],
          ['Compare results', 'Simulation A against B', () => ctx.go('comparison')],
          ['Run validation', 'Checks with their evidence', () => ctx.go('validation')],
          ['Review diagnostics', 'Findings by severity', () => ctx.go('diagnostics')],
          ['Generate a report', 'Markdown or HTML', () => ctx.go('reports')],
        ].map(([title, sub, fn]) => (
          <button key={String(title)} onClick={fn as () => void}>
            <b>{title as string}</b><i>{sub as string}</i>
          </button>
        ))}
      </div>

      <div className="grid g2">
        <Slab title="Loaded simulations">
          <table className="data">
            <thead><tr><th>Simulation</th><th>Domain</th><th>Fields</th><th>Validation</th></tr></thead>
            <tbody>
              {rows.map(({ sim, validation }) => (
                <tr key={sim.id} className="clickrow"
                    onClick={() => ctx.go(DOMAIN_VIEW[sim.domain] ?? 'simulations', sim.id)}>
                  <td>
                    <b style={{ fontWeight: 500 }}>{sim.name}</b><br />
                    <span className="num" style={{ color: 'var(--ink-3)', fontSize: 11 }}>
                      {sim.id} · {sim.nodes.toLocaleString()} nodes
                    </span>
                  </td>
                  <td>{sim.domain}</td>
                  <td className="n">{sim.fields.length}</td>
                  <td><StatusPill status={validation.overall} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Slab>

        <Slab title="Findings needing attention"
              right={<button className="btn sm" onClick={() => ctx.go('diagnostics')}>All diagnostics</button>}>
          <table className="data">
            <thead><tr><th>Finding</th><th>Simulation</th><th>Severity</th></tr></thead>
            <tbody>
              {rows.flatMap(({ sim, diagnostics }) =>
                diagnostics.findings.filter((f) => f.severity !== 'info').map((f, i) => (
                  <tr key={`${sim.id}-${i}`} className="clickrow" onClick={() => ctx.go('diagnostics', sim.id)}>
                    <td>{f.title}</td>
                    <td className="num" style={{ fontSize: 11.5 }}>{sim.id}</td>
                    <td><span className={`pill ${f.severity === 'critical' ? 'crit' : 'warn'}`}>
                      {f.severity === 'critical' ? 'Critical' : 'Warning'}</span></td>
                  </tr>
                )),
              )}
              {!rows.some((r) => r.diagnostics.findings.some((f) => f.severity !== 'info')) && (
                <tr><td colSpan={3} style={{ color: 'var(--ink-3)' }}>No critical or warning findings.</td></tr>
              )}
            </tbody>
          </table>
        </Slab>
      </div>
    </div>
  )
}
