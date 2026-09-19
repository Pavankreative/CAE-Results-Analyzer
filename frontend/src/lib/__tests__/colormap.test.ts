import { describe, expect, it } from 'vitest'
import { colormap, COLORMAPS } from '../colormap'
import { num, percent } from '../format'

describe('colormap', () => {
  it('clamps values outside 0..1', () => {
    expect(colormap('jet', -5)).toEqual(colormap('jet', 0))
    expect(colormap('jet', 5)).toEqual(colormap('jet', 1))
  })

  it('returns channels inside the 0..255 range for every map', () => {
    for (const name of COLORMAPS) {
      for (const t of [0, 0.25, 0.5, 0.75, 1]) {
        for (const c of colormap(name, t)) {
          expect(c).toBeGreaterThanOrEqual(0)
          expect(c).toBeLessThanOrEqual(255)
        }
      }
    }
  })

  it('interpolates between stops rather than snapping', () => {
    const mid = colormap('coolwarm', 0.5)
    const low = colormap('coolwarm', 0)
    expect(mid).not.toEqual(low)
  })

  it('handles a non-finite input without throwing', () => {
    expect(() => colormap('viridis', Number.NaN)).not.toThrow()
  })
})

describe('formatting', () => {
  it('renders an em dash for missing numbers', () => {
    expect(num(null)).toBe('—')
    expect(num(Number.NaN)).toBe('—')
  })

  it('switches to exponential for very large and very small values', () => {
    expect(num(1.2e-6)).toContain('e')
    expect(num(5e8)).toContain('e')
  })

  it('signs percentage changes', () => {
    expect(percent(3.21)).toBe('+3.2 %')
    expect(percent(-3.21)).toBe('-3.2 %')
    expect(percent(null)).toBe('—')
  })
})
