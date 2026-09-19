import type { ReactNode } from 'react'
import { SEVERITY_LABEL, SEVERITY_PILL, STATUS_LABEL, STATUS_PILL } from '../lib/format'

export function Pill({ kind, children }: { kind: string; children: ReactNode }) {
  return <span className={`pill ${kind}`}>{children}</span>
}

export function StatusPill({ status }: { status: string }) {
  return <Pill kind={STATUS_PILL[status] ?? 'idle'}>{STATUS_LABEL[status] ?? status}</Pill>
}

export function SeverityPill({ severity }: { severity: string }) {
  return <Pill kind={SEVERITY_PILL[severity] ?? 'idle'}>{SEVERITY_LABEL[severity] ?? severity}</Pill>
}

export function Slab({ title, right, children, style }:
  { title?: ReactNode; right?: ReactNode; children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div className="slab" style={style}>
      {title && <header>{title}{right && <span className="r">{right}</span>}</header>}
      {children}
    </div>
  )
}

export function KeyValues({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <table className="data">
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={`${k}-${i}`}>
            <td style={{ color: 'var(--ink-3)' }}>{k}</td>
            <td className="n">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function EvidenceTable({ rows, caption = 'evidence' }:
  { rows: { label: string; value: string | number }[]; caption?: string }) {
  if (!rows.length) return <p className="hint">No evidence recorded for this item.</p>
  return (
    <div className="evidence">
      <div className="eh">{caption}</div>
      <table className="data">
        <tbody>
          {rows.map((e, i) => (
            <tr key={i}><td style={{ color: 'var(--ink-3)' }}>{e.label}</td><td className="n">{String(e.value)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Loading({ what }: { what: string }) {
  return <div className="empty"><b>Loading {what}</b>Reading from the result model.</div>
}

export function ErrorNote({ error }: { error: string }) {
  return (
    <div className="empty">
      <b>Could not load this view</b>
      {error}
      <p className="hint">Check that the backend is running: <code>uvicorn app.main:app --reload</code></p>
    </div>
  )
}
