import { useEffect, useMemo, useRef, useState } from 'react'
import type { AppContext } from '../App'
import FindingCard from '../components/FindingCard'
import Legend from '../components/Legend'
import Plot from '../components/Plot'
import { ErrorNote, EvidenceTable, Loading, StatusPill } from '../components/Primitives'
import Viewport from '../components/Viewport'
import { api } from '../lib/api'
import { COLORMAPS, type ColormapName } from '../lib/colormap'
import { num } from '../lib/format'
import { useAsync } from '../lib/hooks'

type DockTab = 'plots' | 'statistics' | 'calculations' | 'diagnostics' | 'validation'
type PropTab = 'properties' | 'results' | 'filters' | 'controls'

interface Probe { value: number; node: number; xyz: [number, number, number] }

export default function Workspace({ ctx, domain }: { ctx: AppContext; domain: string }) {
  const sim = useMemo(
    () => ctx.simulations.find((s) => s.id === ctx.active?.id && s.domain === domain)
      ?? ctx.simulations.find((s) => s.domain === domain) ?? null,
    [ctx.simulations, ctx.active, domain],
  )

  const [field, setField] = useState<string>('')
  const [step, setStep] = useState(-1)
  const [cmap, setCmap] = useState<ColormapName>('jet')
  const [range, setRange] = useState<[number, number]>([0, 1])
  const [wireframe, setWireframe] = useState(false)
  const [transparent, setTransparent] = useState(false)
  const [clip, setClip] = useState({ on: false, axis: 'x' as 'x' | 'y' | 'z', position: 0.5 })
  const [hidden, setHidden] = useState<Set<number>>(new Set())
  const [deform, setDeform] = useState(0)
  const [dock, setDock] = useState<DockTab>('plots')
  const [propTab, setPropTab] = useState<PropTab>('properties')
  const [probes, setProbes] = useState<Probe[]>([])
  const [viewCommand, setViewCommand] = useState<{ name: string; nonce: number } | null>(null)
  const [playing, setPlaying] = useState(false)
  const [openSections, setOpenSections] = useState<Set<string>>(new Set(['Geometry', 'Results']))
  const layout = useRef<HTMLDivElement>(null)

  const detail = useAsync(() => sim ? api.simulation(sim.id) : Promise.reject(new Error('no simulation')), [sim?.id])
  const mesh = useAsync(() => sim ? api.mesh(sim.id) : Promise.reject(new Error('no simulation')), [sim?.id])

  useEffect(() => {
    if (sim && !sim.fields.some((f) => f.name === field)) {
      setField(sim.fields[0]?.name ?? '')
      setRange([0, 1])
      setStep(-1)
      setProbes([])
    }
  }, [sim, field])

  // A filter request from the assistant selects the field and clamps the range.
  useEffect(() => {
    const req = ctx.filterRequest
    if (!req || !sim) return
    if (sim.fields.some((f) => f.name === req.field)) {
      setField(req.field)
      setRange([req.fraction, 1])
      setPropTab('filters')
    }
  }, [ctx.filterRequest, sim])

  const values = useAsync(
    () => sim && field ? api.fieldValues(sim.id, field, step) : Promise.reject(new Error('no field')),
    [sim?.id, field, step],
  )
  const stats = useAsync(
    () => sim && field ? api.fieldStatistics(sim.id, field, step) : Promise.reject(new Error('no field')),
    [sim?.id, field, step],
  )
  const calcs = useAsync(() => sim ? api.calculations(sim.id) : Promise.resolve([]), [sim?.id])
  const diag = useAsync(() => sim ? api.diagnostics(sim.id) : Promise.reject(new Error('no simulation')), [sim?.id])
  const valid = useAsync(() => sim ? api.validation(sim.id) : Promise.reject(new Error('no simulation')), [sim?.id])

  const nSteps = values.data?.steps.length ?? 1
  const currentStep = step < 0 ? nSteps - 1 : step

  useEffect(() => {
    if (!playing || nSteps < 2) return
    const timer = window.setInterval(() => {
      setStep((s) => ((s < 0 ? nSteps - 1 : s) + 1) % nSteps)
    }, 260)
    return () => window.clearInterval(timer)
  }, [playing, nSteps])

  // Resizable panels: the splitters write CSS variables on the grid container.
  const startDrag = (kind: 'left' | 'right' | 'bottom') => (e: React.PointerEvent) => {
    e.preventDefault()
    const el = layout.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const move = (ev: PointerEvent) => {
      if (kind === 'left') el.style.setProperty('--lw', `${Math.min(460, Math.max(180, ev.clientX - rect.left))}px`)
      if (kind === 'right') el.style.setProperty('--rw', `${Math.min(520, Math.max(220, rect.right - ev.clientX))}px`)
      if (kind === 'bottom') el.style.setProperty('--bh', `${Math.min(rect.height - 200, Math.max(90, rect.bottom - ev.clientY))}px`)
    }
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }

  if (!sim) {
    return (
      <div className="empty">
        <b>No {domain} result is loaded</b>
        Import a {domain} result file, or generate the sample datasets with
        <code> python scripts/generate_samples.py</code>.
      </div>
    )
  }
  if (detail.error || mesh.error) return <ErrorNote error={detail.error ?? mesh.error ?? ''} />
  if (!detail.data || !mesh.data) return <Loading what={sim.name} />

  const d = detail.data
  const activeField = sim.fields.find((f) => f.name === field)
  const categories = [...new Set(sim.fields.map((f) => f.category))]
  const toggleSection = (name: string) => {
    const next = new Set(openSections)
    next.has(name) ? next.delete(name) : next.add(name)
    setOpenSections(next)
  }
  const section = (name: string, count: number, rows: JSX.Element[]) => (
    <div key={name}>
      <div className="node" onClick={() => toggleSection(name)}>
        <span className="tw">{openSections.has(name) ? '▾' : '▸'}</span>
        <span>{name}</span><span className="meta">{count}</span>
      </div>
      <div className={`kids${openSections.has(name) ? ' open' : ''}`}>{rows}</div>
    </div>
  )

  return (
    <div className="ws" ref={layout}>
      {/* ------------------------------------------------------------ tree */}
      <section className="pane tree">
        <header>Project tree<span className="r"><span className="num" style={{ fontSize: 10 }}>{sim.id}</span></span></header>
        <div className="fill">
          {section('Geometry', mesh.data.parts.length, mesh.data.parts.map((p, i) => (
            <div className="node" key={p} style={{ paddingLeft: 26 }}
                 onClick={() => {
                   const next = new Set(hidden)
                   next.has(i) ? next.delete(i) : next.add(i)
                   setHidden(next)
                 }}>
              <span className="tw">{hidden.has(i) ? '○' : '◉'}</span><span>{p}</span>
            </div>
          )))}
          {section('Mesh', Object.keys(d.mesh_metrics).length,
            Object.entries(d.mesh_metrics).map(([k, v]) => (
              <div className="node" key={k} style={{ paddingLeft: 26 }}>
                <span className="tw" /><span>{k}</span><span className="meta">{String(v)}</span>
              </div>
            )))}
          {section('Materials', d.materials.length, d.materials.map((m, i) => (
            <div className="node" key={i} style={{ paddingLeft: 26 }}>
              <span className="tw" /><span>{String(m.name)}</span>
            </div>
          )))}
          {section('Boundary conditions', d.boundary_conditions.length, d.boundary_conditions.map((b) => (
            <div className="node" key={b.name} style={{ paddingLeft: 26 }}>
              <span className="tw" /><span>{b.name}</span><span className="meta">{b.kind}</span>
            </div>
          )))}
          {section('Loads', d.loads.length, d.loads.map((l) => (
            <div className="node" key={l.name} style={{ paddingLeft: 26 }}>
              <span className="tw" /><span>{l.name}</span>
            </div>
          )))}
          {section('Simulation cases', d.load_cases.length, d.load_cases.map((c, i) => (
            <div className={`node${i === 0 ? ' on' : ''}`} key={c} style={{ paddingLeft: 26 }}>
              <span className="tw">{i === 0 ? '◉' : '○'}</span><span>{c}</span>
              {i === 0 && <span className="meta">loaded</span>}
            </div>
          )))}
          {section('Results', sim.fields.length, categories.flatMap((cat) => [
            <div className="node" key={`c-${cat}`} style={{ paddingLeft: 24, color: 'var(--ink-3)' }}>
              <span className="tw" /><span>{cat}</span>
            </div>,
            ...sim.fields.filter((f) => f.category === cat).map((f) => (
              <div className={`node${f.name === field ? ' on' : ''}`} key={f.name}
                   style={{ paddingLeft: 38 }}
                   onClick={() => { setField(f.name); setRange([0, 1]); setStep(-1) }}>
                <span className="tw" /><span>{f.label}</span><span className="meta">{f.unit}</span>
              </div>
            )),
          ]))}
        </div>
      </section>
      <div className="split v a" onPointerDown={startDrag('left')} />

      {/* -------------------------------------------------------- viewport */}
      <section className="pane vp">
        <div className="tabs">
          {categories.map((cat) => (
            <button key={cat} className={activeField?.category === cat ? 'on' : ''}
                    onClick={() => {
                      const first = sim.fields.find((f) => f.category === cat)
                      if (first) { setField(first.name); setRange([0, 1]) }
                    }}>{cat}</button>
          ))}
        </div>
        <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex' }}>
          <Viewport
            mesh={mesh.data}
            values={values.data?.values ?? null}
            range={range}
            min={values.data?.min ?? 0}
            max={values.data?.max ?? 1}
            unit={values.data?.unit ?? ''}
            cmap={cmap}
            wireframe={wireframe}
            transparent={transparent}
            clip={clip}
            hiddenParts={hidden}
            deformScale={deform}
            viewCommand={viewCommand}
            onProbe={(p) => setProbes((list) => [...list, p])}
          />
          <div className="vptools">
            {['fit', 'iso', 'front', 'top', 'right'].map((v) => (
              <button key={v} className="vptool" title={v}
                      onClick={() => setViewCommand({ name: v, nonce: Date.now() })}>
                <span style={{ fontSize: 9 }}>{v.slice(0, 3)}</span>
              </button>
            ))}
            <button className={`vptool${wireframe ? ' on' : ''}`} title="Wireframe"
                    onClick={() => setWireframe(!wireframe)}><span style={{ fontSize: 9 }}>wir</span></button>
            <button className={`vptool${transparent ? ' on' : ''}`} title="Transparency"
                    onClick={() => setTransparent(!transparent)}><span style={{ fontSize: 9 }}>tra</span></button>
            <button className={`vptool${clip.on ? ' on' : ''}`} title="Section plane"
                    onClick={() => setClip({ ...clip, on: !clip.on })}><span style={{ fontSize: 9 }}>sec</span></button>
            <button className="vptool" title="Clear probes"
                    onClick={() => { setProbes([]); setViewCommand({ name: 'clear', nonce: Date.now() }) }}>
              <span style={{ fontSize: 9 }}>clr</span></button>
          </div>
          {values.data && (
            <Legend label={values.data.label} unit={values.data.unit}
                    min={values.data.min} max={values.data.max} range={range} cmap={cmap} />
          )}
          <div className="vpfoot">
            <button className="btn sm" onClick={() => setPlaying(!playing)} disabled={nSteps < 2}>
              {playing ? 'Pause' : 'Play'}
            </button>
            <span>step {currentStep + 1} / {nSteps}</span>
            <input type="range" min={0} max={Math.max(0, nSteps - 1)} value={currentStep}
                   onChange={(e) => setStep(Number(e.target.value))} disabled={nSteps < 2} />
            <span>{values.data ? `${num(values.data.min, 2)} … ${num(values.data.max, 2)} ${values.data.unit}` : '—'}</span>
          </div>
        </div>
      </section>
      <div className="split v b" onPointerDown={startDrag('right')} />
      <div className="split h" onPointerDown={startDrag('bottom')} />

      {/* ------------------------------------------------------------ dock */}
      <section className="pane dock">
        <div className="tabs">
          {(['plots', 'statistics', 'calculations', 'diagnostics', 'validation'] as DockTab[]).map((t) => (
            <button key={t} className={dock === t ? 'on' : ''} onClick={() => setDock(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
        <div className="fill">
          {dock === 'plots' && (
            <div className="plotwrap" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(340px,1fr))' }}>
              {stats.data?.envelope && stats.data.envelope.steps.length > 1 && (
                <Plot title={`${stats.data.label} over the solution steps`}
                      xLabel="step" yLabel={stats.data.unit}
                      series={[
                        { name: 'max', points: stats.data.envelope.steps.map((s, i) => [s, stats.data!.envelope!.max[i]] as [number, number]) },
                        { name: 'mean', points: stats.data.envelope.steps.map((s, i) => [s, stats.data!.envelope!.mean[i]] as [number, number]) },
                      ]} />
              )}
              {d.convergence && Object.entries(d.convergence.monitors)
                .filter(([k]) => !['cd', 'cl'].includes(k))
                .slice(0, 1)
                .map(([, ]) => (
                  <Plot key="residuals" title="Residual history" xLabel="iteration" yLabel="log residual" logY
                        series={Object.entries(d.convergence!.monitors)
                          .filter(([k]) => !['cd', 'cl'].includes(k))
                          .map(([k, v]) => ({
                            name: k,
                            points: d.convergence!.iterations.map((it, i) => [it, v[i]] as [number, number]),
                          }))} />
                ))}
              {d.convergence?.monitors.cd && (
                <Plot title="Monitored drag coefficient" xLabel="iteration" yLabel="Cd"
                      series={[{ name: 'cd', points: d.convergence.iterations.map((it, i) => [it, d.convergence!.monitors.cd[i]] as [number, number]) }]} />
              )}
              {!d.convergence && (!stats.data?.envelope || stats.data.envelope.steps.length < 2) && (
                <div className="empty"><b>No history to plot</b>
                  This result carries a single step and no convergence monitors.</div>
              )}
            </div>
          )}

          {dock === 'statistics' && stats.data && (
            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 14, padding: 10 }}>
              <div className="slab">
                <header>{stats.data.label} · step {currentStep + 1}</header>
                <table className="data">
                  <tbody>
                    {([
                      ['Sample points', stats.data.count.toLocaleString()],
                      ['Minimum', `${num(stats.data.minimum.value)} ${stats.data.unit}`],
                      ['Maximum', `${num(stats.data.maximum.value)} ${stats.data.unit}`],
                      ['Mean', `${num(stats.data.mean)} ${stats.data.unit}`],
                      ['Standard deviation', `${num(stats.data.std)} ${stats.data.unit}`],
                      ['Median', `${num(stats.data.median)} ${stats.data.unit}`],
                      ['P95', `${num(stats.data.p95)} ${stats.data.unit}`],
                      ['P99', `${num(stats.data.p99)} ${stats.data.unit}`],
                      ['Non-finite values', stats.data.nan_count],
                      ['Maximum at node', stats.data.maximum.node_id ?? '—'],
                    ] as [string, string | number][]).map(([k, v]) => (
                      <tr key={k}><td style={{ color: 'var(--ink-3)' }}>{k}</td><td className="n">{v}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="slab">
                <header>Distribution</header>
                <div style={{ padding: 10 }}>
                  {stats.data.histogram && (
                    <Plot title={`${stats.data.label} [${stats.data.unit}]`} xLabel="value" yLabel="count"
                          height={150}
                          series={[{
                            name: 'count',
                            points: stats.data.histogram.counts.map((c, i) => [
                              (stats.data!.histogram!.edges[i] + stats.data!.histogram!.edges[i + 1]) / 2, c,
                            ] as [number, number]),
                          }]} />
                  )}
                  <p className="hint" style={{ padding: '0 2px' }}>
                    Computed over every node of the field at this step by the backend, not sampled in the browser.
                  </p>
                </div>
              </div>
            </div>
          )}

          {dock === 'calculations' && (
            <div style={{ padding: 10, display: 'grid', gap: 10,
                          gridTemplateColumns: 'repeat(auto-fit,minmax(330px,1fr))' }}>
              {(calcs.data ?? []).map((c) => (
                <div className="calc" key={c.name}>
                  <div className="ch">{c.name}<span className="pill info" style={{ marginLeft: 'auto' }}>derived</span></div>
                  <div className="formula">{c.formula}</div>
                  <div className="ins">
                    {c.inputs.map((i) => (
                      <div key={i.name}><span style={{ color: 'var(--ink-3)' }}>{i.name}</span>
                        <span>{String(i.value)} {i.unit}</span></div>
                    ))}
                  </div>
                  <div className="res">
                    <span style={{ color: 'var(--ink-3)', fontSize: 11.5 }}>Result</span>
                    <b>{num(c.result)} <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{c.unit}</span></b>
                  </div>
                  <div className="assump">
                    <b style={{ color: 'var(--ink-2)', fontWeight: 500 }}>Assumptions. </b>{c.assumptions}
                  </div>
                </div>
              ))}
              {!calcs.data?.length && <div className="empty"><b>No derived quantities</b>
                This simulation does not carry the inputs any standard calculation needs.</div>}
            </div>
          )}

          {dock === 'diagnostics' && (
            <div style={{ padding: 10, display: 'grid', gap: 8 }}>
              {(diag.data?.findings ?? []).map((f, i) => <FindingCard key={i} finding={f} />)}
              {!diag.data?.findings.length && <div className="empty"><b>No findings</b>
                No diagnostic rule fired on this result set.</div>}
            </div>
          )}

          {dock === 'validation' && valid.data && (
            <table className="data">
              <thead><tr><th>Check</th><th>Status</th><th>Finding</th></tr></thead>
              <tbody>
                {valid.data.checks.map((c) => (
                  <tr key={c.name}>
                    <td><b style={{ fontWeight: 500 }}>{c.name}</b></td>
                    <td><StatusPill status={c.status} /></td>
                    <td style={{ color: 'var(--ink-2)' }}>{c.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ----------------------------------------------------------- props */}
      <section className="pane props">
        <div className="tabs">
          {(['properties', 'results', 'filters', 'controls'] as PropTab[]).map((t) => (
            <button key={t} className={propTab === t ? 'on' : ''} onClick={() => setPropTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
        <div className="fill">
          {propTab === 'properties' && (
            <>
              <div className="psec">simulation</div>
              {([['Name', sim.name], ['Domain', sim.domain], ['Analysis', sim.analysis_type],
                 ['Solver', sim.solver], ['Source', sim.source_file || '—'], ['Adapter', sim.adapter],
                 ['Sample data', sim.is_sample_data ? 'yes' : 'no']] as [string, string][]).map(([k, v]) => (
                <div className="prow" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
              ))}
              <div className="psec">active result</div>
              {stats.data && ([
                ['Variable', stats.data.label], ['Unit', stats.data.unit],
                ['Maximum', num(stats.data.maximum.value)], ['Minimum', num(stats.data.minimum.value)],
                ['Max at node', String(stats.data.maximum.node_id ?? '—')],
                ['Coordinates', stats.data.maximum.coordinates?.map((c) => c.toFixed(1)).join(', ') ?? '—'],
              ] as [string, string][]).map(([k, v]) => (
                <div className="prow" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
              ))}
              <div className="psec">probes</div>
              {probes.length === 0 && <div className="prow"><span className="k">Click the model to place a probe</span></div>}
              {probes.map((p, i) => (
                <div className="prow" key={i}>
                  <span className="k">P{i + 1} ({p.xyz.map((c) => c.toFixed(1)).join(', ')})</span>
                  <span className="v">{num(p.value)} {values.data?.unit}</span>
                </div>
              ))}
              <div className="psec">materials</div>
              {d.materials.map((m, i) => (
                <div className="prow" key={i}>
                  <span className="k" style={{ flex: 'none', width: '100%' }}>
                    <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{String(m.name)}</b><br />
                    <span style={{ fontSize: 11 }}>
                      {Object.entries(m).filter(([k]) => k !== 'name')
                        .map(([k, v]) => `${k} ${v}`).join(' · ')}
                    </span>
                  </span>
                </div>
              ))}
            </>
          )}

          {propTab === 'results' && (
            <>
              {categories.map((cat) => (
                <div key={cat}>
                  <div className="psec">{cat.toLowerCase()}</div>
                  <div className="varlist">
                    {sim.fields.filter((f) => f.category === cat).map((f) => (
                      <button key={f.name} className={f.name === field ? 'on' : ''}
                              onClick={() => { setField(f.name); setRange([0, 1]) }}>
                        {f.label}<span className="u">{f.unit}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <div className="ctl">
                <button className="btn sm" onClick={async () => {
                  if (!sim) return
                  try {
                    const r = await api.derivedField(sim.id, field)
                    ctx.toast(`Derived field created: ${r.label}`)
                  } catch (e) {
                    ctx.toast((e as Error).message)
                  }
                }}>Compute safety factor field</button>
              </div>
            </>
          )}

          {propTab === 'filters' && values.data && (
            <>
              <div className="psec">value range</div>
              <div className="ctl">
                <label>Lower bound<b>{num(values.data.min + (values.data.max - values.data.min) * range[0])} {values.data.unit}</b></label>
                <input type="range" min={0} max={100} value={range[0] * 100}
                       onChange={(e) => setRange([Math.min(Number(e.target.value) / 100, range[1]), range[1]])} />
              </div>
              <div className="ctl">
                <label>Upper bound<b>{num(values.data.min + (values.data.max - values.data.min) * range[1])} {values.data.unit}</b></label>
                <input type="range" min={0} max={100} value={range[1] * 100}
                       onChange={(e) => setRange([range[0], Math.max(Number(e.target.value) / 100, range[0])])} />
              </div>
              <div className="ctl">
                <label>Colour map</label>
                <select value={cmap} onChange={(e) => setCmap(e.target.value as ColormapName)}>
                  {COLORMAPS.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="psec">threshold selection</div>
              <div className="ctl" style={{ gap: 6 }}>
                {[0.8, 0.9].map((f) => (
                  <button className="btn sm" key={f} onClick={async () => {
                    const r = await api.filter(sim.id, { field, step, fraction_of_max: f })
                    setRange([f, 1])
                    ctx.toast(`${r.selected.toLocaleString()} of ${r.total.toLocaleString()} nodes at or above ${Math.round(f * 100)} % of the peak`)
                  }}>Select above {Math.round(f * 100)} % of the peak</button>
                ))}
                <button className="btn sm" onClick={() => setRange([0, 1])}>Reset to full range</button>
              </div>
              <div className="psec">section plane</div>
              <label className="chk">
                <input type="checkbox" checked={clip.on} onChange={(e) => setClip({ ...clip, on: e.target.checked })} />
                Section plane active
              </label>
              <div className="ctl">
                <label>Axis</label>
                <select value={clip.axis} onChange={(e) => setClip({ ...clip, axis: e.target.value as 'x' | 'y' | 'z' })}>
                  <option value="x">x</option><option value="y">y</option><option value="z">z</option>
                </select>
              </div>
              <div className="ctl">
                <label>Position<b>{Math.round(clip.position * 100)} %</b></label>
                <input type="range" min={0} max={100} value={clip.position * 100}
                       onChange={(e) => setClip({ ...clip, position: Number(e.target.value) / 100 })} />
              </div>
              <div className="psec">visibility</div>
              {mesh.data.parts.map((p, i) => (
                <label className="chk" key={p}>
                  <input type="checkbox" checked={!hidden.has(i)} onChange={(e) => {
                    const next = new Set(hidden)
                    e.target.checked ? next.delete(i) : next.add(i)
                    setHidden(next)
                  }} />
                  {p}
                </label>
              ))}
            </>
          )}

          {propTab === 'controls' && (
            <>
              <div className="psec">display</div>
              <div className="ctl">
                <label>Deformation scale<b>{deform}×</b></label>
                <input type="range" min={0} max={40} value={deform}
                       onChange={(e) => setDeform(Number(e.target.value))} />
              </div>
              <label className="chk"><input type="checkbox" checked={wireframe}
                     onChange={(e) => setWireframe(e.target.checked)} /> Wireframe</label>
              <label className="chk"><input type="checkbox" checked={transparent}
                     onChange={(e) => setTransparent(e.target.checked)} /> Transparency</label>
              <div className="psec">view</div>
              <div className="ctl" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5 }}>
                {['iso', 'front', 'top', 'right', 'left', 'fit'].map((v) => (
                  <button className="btn sm" key={v}
                          onClick={() => setViewCommand({ name: v, nonce: Date.now() })}>{v}</button>
                ))}
              </div>
              <div className="psec">validation summary</div>
              {valid.data && (
                <div className="prow"><span className="k">Overall</span>
                  <span className="v"><StatusPill status={valid.data.overall} /></span></div>
              )}
              {valid.data?.checks.slice(0, 4).map((c) => (
                <div className="prow" key={c.name}><span className="k">{c.name}</span>
                  <span className="v" style={{ fontSize: 11 }}>{c.status.replace('_', ' ')}</span></div>
              ))}
              <div className="psec">evidence for the active field</div>
              {stats.data && (
                <div style={{ padding: 10 }}>
                  <EvidenceTable caption="statistics used by the checks" rows={[
                    { label: 'maximum', value: `${num(stats.data.maximum.value)} ${stats.data.unit}` },
                    { label: 'mean', value: `${num(stats.data.mean)} ${stats.data.unit}` },
                    { label: 'P95', value: `${num(stats.data.p95)} ${stats.data.unit}` },
                    { label: 'sample points', value: stats.data.count.toLocaleString() },
                  ]} />
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  )
}
