import { num } from '../lib/format'

export interface Series {
  name: string
  points: [number, number][]
}

interface Props {
  title: string
  xLabel: string
  yLabel: string
  series: Series[]
  height?: number
  logY?: boolean
}

const COLORS = ['var(--accent)', 'var(--warn)', 'var(--pass)', 'var(--crit)']

/** Small SVG line chart used for residuals, histories and overlays. */
export default function Plot({ title, xLabel, yLabel, series, height = 160, logY = false }: Props) {
  const W = 560
  const H = height
  const L = 52
  const R = 12
  const T = 20
  const B = 26
  const mapped = series.map((s) => ({
    ...s,
    points: s.points
      .filter(([, y]) => Number.isFinite(y) && (!logY || y > 0))
      .map(([x, y]) => [x, logY ? Math.log10(y) : y] as [number, number]),
  })).filter((s) => s.points.length > 1)

  if (!mapped.length) {
    return <div className="empty"><b>No series to plot</b>This result set carries no history for that quantity.</div>
  }
  const all = mapped.flatMap((s) => s.points)
  const xs = all.map((p) => p[0])
  const ys = all.map((p) => p[1])
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)]
  const pad = (y1 - y0) * 0.12 || 1
  y0 -= pad; y1 += pad
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const X = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R)
  const Y = (v: number) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T - B)
  const fmtY = (v: number) => (logY ? `1e${v.toFixed(0)}` : num(v, Math.abs(v) < 10 ? 2 : 0))

  return (
    <svg className="plot" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" role="img"
         aria-label={title}>
      <text className="ttl" x={6} y={11}>{title}</text>
      <line className="ax" x1={L} y1={T} x2={L} y2={H - B} />
      <line className="ax" x1={L} y1={H - B} x2={W - R} y2={H - B} />
      {[0, 1, 2, 3, 4].map((i) => {
        const y = T + (i * (H - T - B)) / 4
        return (
          <g key={`g${i}`}>
            <line className="gl" x1={L} y1={y} x2={W - R} y2={y} />
            <text x={L - 6} y={y + 3} textAnchor="end">{fmtY(y1 - ((y1 - y0) * i) / 4)}</text>
          </g>
        )
      })}
      {[0, 1, 2, 3, 4].map((i) => {
        const x = L + (i * (W - L - R)) / 4
        return <text key={`x${i}`} x={x} y={H - 9} textAnchor="middle">
          {num(x0 + ((x1 - x0) * i) / 4, Math.abs(x1) < 10 ? 1 : 0)}</text>
      })}
      {mapped.map((s, i) => (
        <path key={s.name} fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth={1.6}
              d={s.points.map((p, j) => `${j ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')} />
      ))}
      {mapped.map((s, i) => (
        <g key={`l${s.name}`} transform={`translate(${L + i * 116},${T - 8})`}>
          <rect width={9} height={2.5} y={-3} fill={COLORS[i % COLORS.length]} />
          <text x={13} y={0}>{s.name}</text>
        </g>
      ))}
      <text x={W - R} y={H - 9} textAnchor="end">{xLabel}</text>
      <text x={6} y={H - B + 12}>{yLabel}</text>
    </svg>
  )
}
