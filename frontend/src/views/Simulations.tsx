import type { AppContext } from '../App'
import { DOMAIN_VIEW } from '../lib/nav'
import { Slab } from '../components/Primitives'

export default function Simulations({ ctx }: { ctx: AppContext }) {
  return (
    <div className="scroll">
      <div className="vhead"><h1>Simulations</h1>
        <p>Every result set currently mapped into the common model.</p></div>
      <div className="sub">Select a row to open it in its domain workspace.</div>
      <Slab>
        <table className="data">
          <thead>
            <tr><th>Simulation</th><th>Domain</th><th>Analysis type</th><th>Solver</th>
              <th>Nodes</th><th>Fields</th><th>Load cases</th><th>Source</th></tr>
          </thead>
          <tbody>
            {ctx.simulations.map((s) => (
              <tr key={s.id} className="clickrow"
                  onClick={() => ctx.go(DOMAIN_VIEW[s.domain] ?? 'home', s.id)}>
                <td><b style={{ fontWeight: 500 }}>{s.name}</b><br />
                  <span className="num" style={{ color: 'var(--ink-3)', fontSize: 11 }}>{s.id}</span></td>
                <td>{s.domain}</td>
                <td style={{ color: 'var(--ink-2)' }}>{s.analysis_type}</td>
                <td style={{ fontSize: 11.5 }}>{s.solver}</td>
                <td className="n">{s.nodes.toLocaleString()}</td>
                <td className="n">{s.fields.length}</td>
                <td className="n">{s.load_cases.length}</td>
                <td className="num" style={{ fontSize: 11 }}>
                  {s.source_file || '—'}<br />
                  <span style={{ color: 'var(--ink-3)' }}>{s.adapter}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Slab>
      <p className="hint">
        Load cases listed without an attached result file are defined in the project but have no data
        imported; the application does not infer results for them.
      </p>
    </div>
  )
}
