import { useState } from 'react'
import type { AppContext } from '../App'
import FindingCard from '../components/FindingCard'
import { ErrorNote, Loading } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import type { Severity } from '../lib/types'

export default function Diagnostics({ ctx }: { ctx: AppContext }) {
  const [filter, setFilter] = useState<Severity | 'all'>('all')
  const all = useAsync(async () => {
    const sims = await api.simulations()
    const reports = await Promise.all(sims.map(async (s) => ({ sim: s, report: await api.diagnostics(s.id) })))
    return reports.flatMap(({ sim, report }) => report.findings.map((f) => ({ sim, finding: f })))
  }, [ctx.simulations.length])

  if (all.error) return <ErrorNote error={all.error} />
  if (!all.data) return <Loading what="diagnostics" />

  const count = (s: Severity) => all.data!.filter((x) => x.finding.severity === s).length
  const shown = all.data.filter((x) => filter === 'all' || x.finding.severity === filter)

  return (
    <div className="scroll">
      <div className="vhead"><h1>Diagnostics</h1>
        <p>Rules over mesh metadata, convergence, value distributions, units and missing data.</p></div>
      <div className="sub">
        Each finding states what was observed, the evidence behind it, a possible cause and what to
        investigate next — not a conclusion about the design.
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <button className={`btn sm${filter === 'all' ? ' primary' : ''}`} onClick={() => setFilter('all')}>
          All findings ({all.data.length})
        </button>
        {(['critical', 'warning', 'info'] as Severity[]).map((s) => (
          <button key={s} className={`btn sm${filter === s ? ' primary' : ''}`} onClick={() => setFilter(s)}>
            {s[0].toUpperCase() + s.slice(1)} ({count(s)})
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gap: 9 }}>
        {shown.map((x, i) => <FindingCard key={i} finding={x.finding} prefix={x.sim.id} />)}
        {!shown.length && <div className="empty"><b>No findings in this category</b>
          Nothing matched the selected severity.</div>}
      </div>
    </div>
  )
}
