import { useState } from 'react'
import type { AppContext } from '../App'
import { EvidenceTable, Loading, Slab } from '../components/Primitives'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import type { AssistantAnswer } from '../lib/types'

const KIND_CLASS: Record<string, string> = {
  simulation_data: 'data', calculated: 'calc', engineering_rule: 'rule',
  interpretation: 'interp', recommendation: 'rec',
}

export default function Assistant({ ctx, onFilter }:
  { ctx: AppContext; onFilter: (field: string, fraction: number) => void }) {
  const [question, setQuestion] = useState('')
  const [thread, setThread] = useState<AssistantAnswer[]>([])
  const [busy, setBusy] = useState(false)
  const meta = useAsync(() => api.suggestions(), [])

  const sim = ctx.active
  const ask = async (q: string) => {
    if (!sim || !q.trim()) return
    setBusy(true)
    try {
      const answer = await api.ask(sim.id, q)
      setThread((t) => [...t, answer])
      setQuestion('')
    } catch (e) {
      ctx.toast((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const runAction = (action: { target: string; params: string }) => {
    if (action.target === 'filter') {
      const [id, field, frac] = action.params.split(':')
      ctx.setActive(id)
      onFilter(field, Number(frac))
      const domainView = { FEA: 'fea', CFD: 'cfd', Thermal: 'thermal', MBD: 'mbd' } as const
      ctx.go(domainView[(sim?.domain ?? 'FEA') as keyof typeof domainView] ?? 'fea', id)
      return
    }
    if (action.target === 'workspace') {
      const [id] = action.params.split(':')
      const domainView = { FEA: 'fea', CFD: 'cfd', Thermal: 'thermal', MBD: 'mbd' } as const
      ctx.go(domainView[(sim?.domain ?? 'FEA') as keyof typeof domainView] ?? 'fea', id)
      return
    }
    ctx.go(action.target as 'validation' | 'diagnostics' | 'comparison' | 'reports', action.params)
  }

  if (!sim) return <div className="empty"><b>No simulation selected</b>Open a result first.</div>

  return (
    <div className="scroll">
      <div className="vhead"><h1>Engineering assistant</h1>
        <p>Answers are assembled from the loaded result model. Each block is labelled by what it is.</p></div>
      <div className="sub">
        No language model runs behind this build: the assistant retrieves statistics, calculations,
        validation results and diagnostic findings, and states where each number came from. An
        unmatched question says so rather than inventing an answer.
      </div>

      <Slab title="Ask about the active simulation"
            right={<span className="num" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{sim.id}</span>}
            style={{ marginBottom: 14 }}>
        <div className="body">
          <div style={{ display: 'flex', gap: 8 }}>
            <input type="text" value={question} placeholder="e.g. Where is maximum stress?"
                   onChange={(e) => setQuestion(e.target.value)}
                   onKeyDown={(e) => e.key === 'Enter' && ask(question)} />
            <button className="btn primary" onClick={() => ask(question)} disabled={busy}>Ask</button>
          </div>
          <div className="chips" style={{ marginTop: 10 }}>
            {(meta.data?.suggestions ?? []).map((s) => (
              <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>
            ))}
          </div>
        </div>
      </Slab>

      {busy && <Loading what="the answer" />}

      {thread.map((a, i) => (
        <Slab key={i} title={a.question}
              right={<span className="pill info">{a.intent}</span>} style={{ marginBottom: 12 }}>
          <div className="body">
            {a.blocks.map((b, j) => (
              <div className={`ab ${KIND_CLASS[b.kind] ?? 'data'}`} key={j}>
                <div className="lbl">{b.label}</div>
                <p>{b.text}</p>
              </div>
            ))}
            <EvidenceTable rows={a.evidence} caption="evidence used for this answer" />
            <div style={{ display: 'flex', gap: 7, marginTop: 10, flexWrap: 'wrap' }}>
              {a.actions.map((act) => (
                <button key={act.label} className="btn sm primary" onClick={() => runAction(act)}>
                  {act.label}
                </button>
              ))}
            </div>
            <p className="hint" style={{ marginTop: 10 }}>{a.disclaimer}</p>
          </div>
        </Slab>
      ))}

      {!thread.length && !busy && (
        <div className="empty"><b>No questions asked yet</b>
          Pick a suggestion above, or type a question about the active result.</div>
      )}
    </div>
  )
}
