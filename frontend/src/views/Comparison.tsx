import { useState } from 'react'
import type { AppContext } from '../App'
import Plot from '../components/Plot'
import { ErrorNote, Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { num, percent } from '../lib/format'
import { useAsync } from '../lib/hooks'

export default function Comparison({ ctx }: { ctx: AppContext }) {
  const sims = ctx.simulations
  const [a, setA] = useState(ctx.active?.id ?? sims[0]?.id ?? '')
  const [b, setB] = useState(sims[1]?.id ?? sims[0]?.id ?? '')
  const cmp = useAsync(() => a && b ? api.compare(a, b) : Promise.reject(new Error('select two simulations')), [a, b])

  if (!sims.length) return <div className="empty"><b>Nothing to compare</b>Load at least one simulation.</div>

  return (
    <div className="scroll">
      <div className="vhead"><h1>Comparison</h1>
        <p>Scalar deltas, pointwise field differences and overlaid histories, computed by the backend
          from both result sets.</p></div>
      <div className="sub">Selecting the same simulation twice is a useful check: every delta should be zero.</div>

      <div className="cmp-heads" style={{ marginBottom: 12 }}>
        {[['Simulation A', a, setA], ['Simulation B', b, setB]].map(([label, value, set]) => (
          <Slab key={label as string} title={label as string}>
            <div className="body">
              <select value={value as string} onChange={(e) => (set as (v: string) => void)(e.target.value)}>
                {sims.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.domain})</option>)}
              </select>
            </div>
          </Slab>
        ))}
      </div>

      {cmp.error && <ErrorNote error={cmp.error} />}
      {cmp.loading && <Loading what="the comparison" />}
      {cmp.data && (
        <>
          <p className="hint" style={{ marginBottom: 12 }}>{cmp.data.mesh_note}</p>
          <div className="grid g2">
            <Slab title="Scalar comparison">
              <table className="data">
                <thead><tr><th>Quantity</th><th>Metric</th><th style={{ textAlign: 'right' }}>A</th>
                  <th style={{ textAlign: 'right' }}>B</th><th style={{ textAlign: 'right' }}>Δ</th></tr></thead>
                <tbody>
                  {cmp.data.scalars.slice(0, 40).map((s, i) => (
                    <tr key={i}>
                      <td>{s.label}<span className="num" style={{ color: 'var(--ink-3)', fontSize: 10.5 }}> [{s.unit}]</span></td>
                      <td style={{ color: 'var(--ink-3)' }}>{s.metric}</td>
                      <td className="n">{num(s.a)}</td>
                      <td className="n">{num(s.b)}</td>
                      <td className="n" style={{ color: s.delta === 0 ? 'var(--ink-3)' : 'var(--ink)' }}>
                        {percent(s.percent)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Slab>

            <Slab title="Pointwise field differences (B − A)">
              {cmp.data.field_differences.length ? (
                <table className="data">
                  <thead><tr><th>Field</th><th style={{ textAlign: 'right' }}>min</th>
                    <th style={{ textAlign: 'right' }}>max</th><th style={{ textAlign: 'right' }}>RMS</th></tr></thead>
                  <tbody>
                    {cmp.data.field_differences.map((d) => (
                      <tr key={d.field}>
                        <td>{d.field}<span className="num" style={{ color: 'var(--ink-3)', fontSize: 10.5 }}> [{d.unit}]</span></td>
                        <td className="n">{num(d.min)}</td><td className="n">{num(d.max)}</td>
                        <td className="n">{num(d.rms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty"><b>Meshes differ</b>
                  Pointwise differences need a common mesh; only scalar comparison is available.</div>
              )}
            </Slab>
          </div>

          {cmp.data.calculations.length > 0 && (
            <Slab title="Derived quantities" style={{ marginTop: 14 }}>
              <table className="data">
                <thead><tr><th>Calculation</th><th style={{ textAlign: 'right' }}>A</th>
                  <th style={{ textAlign: 'right' }}>B</th><th style={{ textAlign: 'right' }}>Change</th></tr></thead>
                <tbody>
                  {cmp.data.calculations.map((c) => (
                    <tr key={c.name}>
                      <td>{c.name} <span className="num" style={{ color: 'var(--ink-3)' }}>[{c.unit}]</span></td>
                      <td className="n">{num(c.a)}</td><td className="n">{num(c.b)}</td>
                      <td className="n">{percent(c.percent)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Slab>
          )}

          {cmp.data.overlays.length > 0 && (
            <div className="grid g2" style={{ marginTop: 14 }}>
              {cmp.data.overlays.slice(0, 4).map((o) => (
                <Slab key={o.field} title={`Overlay: ${o.field}`}>
                  <div className="plotwrap">
                    <Plot title={o.field} xLabel="step / iteration" yLabel={o.unit || '—'}
                          logY={o.field.startsWith('monitor:') && !o.field.includes('cd')}
                          series={[
                            { name: 'A', points: o.a.steps.map((s, i) => [s, o.a.values[i]] as [number, number]) },
                            { name: 'B', points: o.b.steps.map((s, i) => [s, o.b.values[i]] as [number, number]) },
                          ]} />
                  </div>
                </Slab>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
