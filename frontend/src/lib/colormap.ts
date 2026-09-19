export type ColormapName = 'jet' | 'viridis' | 'coolwarm' | 'inferno' | 'steel'

const STOPS: Record<ColormapName, [number, string][]> = {
  jet: [[0, '#00007f'], [0.12, '#0000ff'], [0.32, '#00d4ff'], [0.5, '#7cff79'],
        [0.68, '#ffd400'], [0.88, '#ff3b00'], [1, '#7f0000']],
  viridis: [[0, '#440154'], [0.25, '#3b528b'], [0.5, '#21918c'], [0.75, '#5ec962'], [1, '#fde725']],
  coolwarm: [[0, '#3b4cc0'], [0.25, '#7b9ff9'], [0.5, '#e8e6e2'], [0.75, '#f6a385'], [1, '#b40426']],
  inferno: [[0, '#000004'], [0.25, '#51127c'], [0.5, '#b6377a'], [0.75, '#fb8861'], [1, '#fcfdbf']],
  steel: [[0, '#0f1b26'], [0.3, '#2f5f7a'], [0.6, '#8fb4c2'], [0.85, '#e0d9c6'], [1, '#f6f3ec']],
}

export const COLORMAPS = Object.keys(STOPS) as ColormapName[]

function hex(h: string): [number, number, number] {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
}

/** Map a normalised value in [0,1] to an RGB triple in [0,255]. */
export function colormap(name: ColormapName, t: number): [number, number, number] {
  const stops = STOPS[name] ?? STOPS.jet
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0))
  for (let i = 0; i < stops.length - 1; i++) {
    const [p0, c0] = stops[i]
    const [p1, c1] = stops[i + 1]
    if (x >= p0 && x <= p1) {
      const f = p1 === p0 ? 0 : (x - p0) / (p1 - p0)
      const a = hex(c0)
      const b = hex(c1)
      return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]
    }
  }
  return hex(stops[stops.length - 1][1])
}

/** Paint a vertical colour bar into a canvas, max at the top. */
export function paintLegend(canvas: HTMLCanvasElement, name: ColormapName): void {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const h = canvas.height
  for (let y = 0; y < h; y++) {
    const [r, g, b] = colormap(name, 1 - y / (h - 1))
    ctx.fillStyle = `rgb(${r | 0},${g | 0},${b | 0})`
    ctx.fillRect(0, y, canvas.width, 1)
  }
}
