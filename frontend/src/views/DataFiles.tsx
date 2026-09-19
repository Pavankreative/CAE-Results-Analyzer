import { useRef, useState } from 'react'
import type { AppContext } from '../App'
import { ErrorNote, Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

export default function DataFiles({ ctx, onImported }: { ctx: AppContext; onImported: () => void }) {
  const adapters = useAsync(() => api.adapters(), [])
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState<string[]>([])

  if (adapters.error) return <ErrorNote error={adapters.error} />
  if (!adapters.data) return <Loading what="the adapter registry" />

  const upload = async (file: File) => {
    setBusy(true)
    try {
      const sim = await api.importFile(file)
      setLog((l) => [`${file.name} → ${sim.id} via ${sim.adapter}: ${sim.nodes} nodes, ${sim.fields.length} fields`, ...l])
      ctx.toast(`Imported ${sim.name}`)
      onImported()
    } catch (e) {
      setLog((l) => [`${file.name} → rejected: ${(e as Error).message}`, ...l])
      ctx.toast('Import rejected — see the log')
    } finally {
      setBusy(false)
    }
  }

  const implemented = adapters.data.adapters.filter((a) => a.status === 'implemented')
  const planned = adapters.data.adapters.filter((a) => a.status === 'planned')

  return (
    <div className="scroll">
      <div className="vhead"><h1>Data & files</h1>
        <p>Import a result file through an adapter, or review which formats are supported.</p></div>
      <div className="sub">Files are parsed on the server and mapped into the common result model.</div>

      <Slab title="Import a result" style={{ marginBottom: 14 }}>
        <div className="body">
          <div className="drop" onClick={() => input.current?.click()}
               onDragOver={(e) => e.preventDefault()}
               onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) upload(f) }}>
            <b>{busy ? 'Importing…' : 'Drop a result file here, or click to browse'}</b>
            <span>Implemented: {implemented.flatMap((a) => a.extensions).join(' · ')}</span>
          </div>
          <input ref={input} type="file" style={{ display: 'none' }}
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f) }} />
          {log.length > 0 && (
            <pre className="repview" style={{ marginTop: 12, maxHeight: 160 }}>{log.join('\n')}</pre>
          )}
        </div>
      </Slab>

      <div className="grid g2">
        <Slab title={`Implemented formats (${implemented.length})`}>
          <table className="data">
            <thead><tr><th>Format</th><th>Extensions</th><th>Notes</th></tr></thead>
            <tbody>
              {implemented.map((a) => (
                <tr key={a.key}>
                  <td><b style={{ fontWeight: 500 }}>{a.name}</b><br />
                    <span style={{ color: 'var(--ink-3)', fontSize: 11 }}>{a.solver}</span></td>
                  <td className="num" style={{ fontSize: 11 }}>{a.extensions.join(' ')}</td>
                  <td style={{ color: 'var(--ink-2)', fontSize: 11.5 }}>{a.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Slab>

        <Slab title={`Planned adapters (${planned.length})`}>
          <table className="data">
            <thead><tr><th>Solver</th><th>Extensions</th><th>What a parser would need</th></tr></thead>
            <tbody>
              {planned.map((a) => (
                <tr key={a.key}>
                  <td>{a.solver}</td>
                  <td className="num" style={{ fontSize: 11 }}>{a.extensions.join(' ')}</td>
                  <td style={{ color: 'var(--ink-2)', fontSize: 11.5 }}>{a.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint" style={{ padding: 10 }}>
            Uploading one of these returns an explicit error instead of a partial or guessed result.
          </p>
        </Slab>
      </div>
    </div>
  )
}
