import { useState } from 'react'
import type { Finding } from '../lib/types'
import { EvidenceTable, SeverityPill } from './Primitives'

/** Finding -> Severity -> Evidence -> Location -> Cause -> Suggested investigation. */
export default function FindingCard({ finding, prefix }: { finding: Finding; prefix?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`finding${open ? ' open' : ''}`}>
      <div className="fh" onClick={() => setOpen(!open)} role="button" tabIndex={0}
           onKeyDown={(e) => e.key === 'Enter' && setOpen(!open)}>
        <SeverityPill severity={finding.severity} />
        <span className="ttl">
          {prefix && <span className="num" style={{ color: 'var(--ink-3)', fontSize: 11, marginRight: 8 }}>{prefix}</span>}
          {finding.title}
        </span>
        <span className="loc">{finding.location.split('·')[0]}</span>
      </div>
      <div className="fb">
        <EvidenceTable rows={finding.evidence} />
        <dl className="kv">
          <dt>Location</dt><dd>{finding.location}</dd>
          <dt>Possible cause</dt><dd>{finding.possible_cause}</dd>
          <dt>Suggested investigation</dt><dd>{finding.suggested_investigation}</dd>
          <dt>Rule</dt><dd className="num">{finding.rule}</dd>
        </dl>
      </div>
    </div>
  )
}
