import { useState } from 'react'
import type { AppContext } from '../App'
import { ErrorNote, Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

export default function Reports({ ctx }: { ctx: AppContext }) {
  const meta = useAsync(() => api.reportSections(), [])
  const [chosen, setChosen] = useState<string[] | null>(null)
  const [compareWith, setCompareWith] = useState('')
  const [preview, setPreview] = useState('')
  const [busy, setBusy] = useState(false)

  if (meta.error) return <ErrorNote error={meta.error} />
  if (!meta.data) return <Loading what="the report builder" />
  const sections = chosen ?? meta.data.sections
  const sim = ctx.active

  const build = async (format: 'markdown' | 'html') => {
    if (!sim) { ctx.toast('Select a simulation first'); return }
    setBusy(true)
    try {
      const text = await api.report({
        simulation_id: sim.id, sections, format,
        compare_with: compareWith || undefined,
      })
      setPreview(text)
      if (format === 'html') {
        const blob = new Blob([text], { type: 'text/html' })
        const url = URL.createObjectURL(blob)
        window.open(url, '_blank')
        ctx.toast('HTML report opened in a new tab')
      } else {
        ctx.toast('Markdown report generated')
      }
    } catch (e) {
      ctx.toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const download = () => {
    if (!preview || !sim) return
    const blob = new Blob([preview], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${sim.id}-report.md`
    a.click()
  }

  return (
    <div className="scroll">
      <div className="vhead"><h1>Reports</h1>
        <p>Structured engineering report built from the same data the views show.</p></div>
      <div className="sub">Markdown, HTML and JSON are implemented. Sample datasets are labelled in the report body.</div>

      <div className="rep">
        <Slab title="Sections">
          <div className="body">
            {meta.data.sections.map((s) => (
              <label className="chk" key={s}>
                <input type="checkbox" checked={sections.includes(s)}
                       onChange={(e) => setChosen(e.target.checked
                         ? [...sections, s] : sections.filter((x) => x !== s))} />
                {meta.data!.titles[s]}
              </label>
            ))}
            <div className="ctl" style={{ marginTop: 10 }}>
              <label>Compare with</label>
              <select value={compareWith} onChange={(e) => setCompareWith(e.target.value)}>
                <option value="">— none —</option>
                {ctx.simulations.filter((s) => s.id !== sim?.id)
                  .map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
              <button className="btn primary" disabled={busy} onClick={() => build('markdown')}>
                Generate Markdown
              </button>
              <button className="btn" disabled={busy} onClick={() => build('html')}>Open HTML</button>
              <button className="btn" disabled={!preview} onClick={download}>Download .md</button>
            </div>
          </div>
        </Slab>

        <Slab title={sim ? `Preview · ${sim.name}` : 'Preview'}>
          {preview
            ? <pre className="repview">{preview}</pre>
            : <div className="empty"><b>No report generated yet</b>
                Choose the sections and select a format.</div>}
        </Slab>
      </div>
    </div>
  )
}
