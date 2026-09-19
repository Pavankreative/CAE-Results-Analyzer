import type { AppContext } from '../App'
import { ErrorNote, Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

/**
 * Module registry. Shows which CAE domains and file formats are actually
 * implemented and which are registered interfaces awaiting a parser, straight
 * from the backend rather than from a hardcoded list.
 */
export default function Optimization({ ctx, modulesOnly }: { ctx: AppContext; modulesOnly?: boolean }) {
  const info = useAsync(async () => ({
    domains: (await api.domains()).domains,
    adapters: await api.adapters(),
  }), [])

  if (info.error) return <ErrorNote error={info.error} />
  if (!info.data) return <Loading what="the module registry" />

  const title = modulesOnly ? 'Modules & multiphysics' : 'Optimization & DOE'

  return (
    <div className="scroll">
      <div className="vhead"><h1>{title}</h1>
        <p>What this build can do today, and what is registered but not yet implemented.</p></div>
      <div className="sub">
        Status comes from the backend registry, so this page cannot drift from what the code supports.
      </div>

      {!modulesOnly && (
        <Slab title="Optimization and DOE" style={{ marginBottom: 14 }}>
          <div className="body">
            <p style={{ color: 'var(--ink-2)', fontSize: 12.5, marginTop: 0 }}>
              No optimizer or DOE driver is implemented in this repository. What exists today is the
              part an optimization study needs from a post-processor: a common result model, scalar
              extraction, derived calculations and design-iteration comparison. A study driver would
              sit above those, writing one simulation per design point and reading the same scalars
              back through the comparison engine.
            </p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn sm primary" onClick={() => ctx.go('comparison')}>
                Compare design iterations
              </button>
              <button className="btn sm" onClick={() => ctx.go('simulations')}>Browse result sets</button>
            </div>
          </div>
        </Slab>
      )}

      <div className="grid g2">
        <Slab title="CAE domains">
          <table className="data">
            <thead><tr><th>Domain</th><th>Status</th><th>Loaded datasets</th></tr></thead>
            <tbody>
              {info.data.domains.map((d) => (
                <tr key={d.key}>
                  <td>{d.key}</td>
                  <td><span className={`pill ${d.status === 'implemented' ? 'pass' : 'idle'}`}>
                    {d.status === 'implemented' ? 'Implemented' : 'Planned'}</span></td>
                  <td className="n">{ctx.simulations.filter((s) => s.domain === d.key).length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Slab>

        <Slab title="Result format adapters">
          <table className="data">
            <thead><tr><th>Format</th><th>Extensions</th><th>Status</th></tr></thead>
            <tbody>
              {info.data.adapters.adapters.map((a) => (
                <tr key={a.key}>
                  <td><b style={{ fontWeight: 500 }}>{a.name}</b><br />
                    <span style={{ color: 'var(--ink-3)', fontSize: 11 }}>{a.solver}</span></td>
                  <td className="num" style={{ fontSize: 11 }}>{a.extensions.join(' ')}</td>
                  <td><span className={`pill ${a.status === 'implemented' ? 'pass' : 'idle'}`}>
                    {a.status === 'implemented' ? 'Implemented' : 'Planned'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint" style={{ padding: 10 }}>{info.data.adapters.note}</p>
        </Slab>
      </div>
    </div>
  )
}
