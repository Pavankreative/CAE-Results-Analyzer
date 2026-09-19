import { useState } from 'react'
import type { AppContext } from '../App'
import { ErrorNote, EvidenceTable, Loading, Slab, StatusPill } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

export default function Validation({ ctx }: { ctx: AppContext }) {
  const [open, setOpen] = useState<string | null>(null)
  const reports = useAsync(async () => {
    const sims = await api.simulations()
    return Promise.all(sims.map(async (s) => ({ sim: s, report: await api.validation(s.id) })))
  }, [ctx.simulations.length])

  if (reports.error) return <ErrorNote error={reports.error} />
  if (!reports.data) return <Loading what="validation results" />

  return (
    <div className="scroll">
      <div className="vhead"><h1>Validation centre</h1>
        <p>Each status is produced by a check in the backend and carries the evidence it used.</p></div>
      <div className="sub">
        Verified · Passed with warnings · Requires investigation · Not validated. A check with no data
        stays "Not validated" rather than defaulting to a pass.
      </div>

      {reports.data.map(({ sim, report }) => (
        <Slab key={sim.id} style={{ marginBottom: 14 }}
              title={<>{sim.name}<span className="num" style={{ color: 'var(--ink-3)', fontSize: 11, marginLeft: 8 }}>{sim.id}</span></>}
              right={<StatusPill status={report.overall} />}>
          <table className="data">
            <thead><tr><th style={{ width: 220 }}>Check</th><th style={{ width: 180 }}>Status</th>
              <th>Finding</th><th style={{ width: 90 }} /></tr></thead>
            <tbody>
              {report.checks.map((c) => {
                const key = `${sim.id}-${c.name}`
                return (
                  <>
                    <tr key={key}>
                      <td><b style={{ fontWeight: 500 }}>{c.name}</b></td>
                      <td><StatusPill status={c.status} /></td>
                      <td style={{ color: 'var(--ink-2)' }}>{c.message}</td>
                      <td>
                        <button className="btn sm" onClick={() => setOpen(open === key ? null : key)}>
                          {open === key ? 'Hide' : 'Evidence'}
                        </button>
                      </td>
                    </tr>
                    {open === key && (
                      <tr key={`${key}-ev`}>
                        <td colSpan={4} style={{ background: 'var(--surface)', padding: 10 }}>
                          <EvidenceTable rows={c.evidence} caption="evidence used for this status" />
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </Slab>
      ))}
    </div>
  )
}
