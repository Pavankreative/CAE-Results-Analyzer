/** Number formatting shared by every numeric readout. */
export function num(v: number | null | undefined, decimals = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-3 || a >= 1e6)) return v.toExponential(2)
  return v.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

export function percent(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(decimals)} %`
}

export const STATUS_LABEL: Record<string, string> = {
  verified: 'Verified',
  warning: 'Passed with warnings',
  investigate: 'Requires investigation',
  not_validated: 'Not validated',
}

export const STATUS_PILL: Record<string, string> = {
  verified: 'pass',
  warning: 'warn',
  investigate: 'crit',
  not_validated: 'idle',
}

export const SEVERITY_PILL: Record<string, string> = {
  critical: 'crit',
  warning: 'warn',
  info: 'info',
}

export const SEVERITY_LABEL: Record<string, string> = {
  critical: 'Critical',
  warning: 'Warning',
  info: 'Information',
}
