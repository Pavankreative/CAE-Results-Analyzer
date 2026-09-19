import { useEffect, useRef } from 'react'
import { paintLegend, type ColormapName } from '../lib/colormap'
import { num } from '../lib/format'

interface Props {
  label: string
  unit: string
  min: number
  max: number
  range: [number, number]
  cmap: ColormapName
}

/** Scientific legend: variable, units, range, colour scale. */
export default function Legend({ label, unit, min, max, range, cmap }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    if (canvas.current) paintLegend(canvas.current, cmap)
  }, [cmap])

  const lo = min + (max - min) * range[0]
  const hi = min + (max - min) * range[1]
  const ticks = [0, 1, 2, 3, 4, 5, 6].map((i) => hi - ((hi - lo) * i) / 6)

  return (
    <div className="legend">
      <div className="lt">{label}</div>
      <div className="lu">[{unit || '—'}]</div>
      <div className="bar">
        <canvas ref={canvas} width={16} height={132} />
        <div className="ticks">
          {ticks.map((t, i) => <span key={i}>{num(t, Math.abs(hi) < 10 ? 3 : 1)}</span>)}
        </div>
      </div>
      <div className="ft">
        max {num(max, 3)}<br />min {num(min, 3)}<br />
        {cmap} · {range[0] === 0 && range[1] === 1 ? 'full range' : 'filtered'}
      </div>
    </div>
  )
}
