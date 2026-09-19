export type ViewId =
  | 'home' | 'projects' | 'simulations'
  | 'fea' | 'cfd' | 'thermal' | 'mbd' | 'multiphysics'
  | 'comparison' | 'validation' | 'diagnostics' | 'assistant' | 'optimization'
  | 'reports' | 'data' | 'settings'

export interface NavEntry {
  id: ViewId
  label: string
  icon: string
  domain?: string
}

export const ICONS: Record<string, string> = {
  home: 'M2 7 8 2.5 14 7v6.5a.5.5 0 0 1-.5.5H10V9.5H6V14H2.5a.5.5 0 0 1-.5-.5Z',
  folder: 'M1.5 3.5h4l1.2 1.5h7.8v7.5h-13Z',
  sim: 'M2 12.5 5.5 6l2.6 3.4L10.6 4 14 12.5Z',
  fea: 'M2 13 8 2l6 11Z',
  cfd: 'M1.5 5c3-2 5 2 7.5 0s4-.5 5.5.5M1.5 8.5c3-2 5 2 7.5 0s4-.5 5.5.5M1.5 12c3-2 5 2 7.5 0s4-.5 5.5.5',
  thermal: 'M6 2v7.2a3 3 0 1 0 2 0V2Z',
  mbd: 'M3 12.5 7 6l5 3 2-5',
  multi: 'M8 1.5 14 5v6L8 14.5 2 11V5Z',
  cmp: 'M7 2v12M2.5 5.5h3M2.5 9h3M10.5 5.5h3M10.5 9h3',
  val: 'M3 8.4 6.3 12 13 4',
  diag: 'M8 2 15 14H1ZM8 6.5v3.2M8 11.4v.9',
  ai: 'M8 2.2 9.6 6.4 14 8l-4.4 1.6L8 13.8 6.4 9.6 2 8l4.4-1.6Z',
  opt: 'M2 13V6M6 13V3M10 13V8M14 13V5',
  rep: 'M4 2h6l3 3v9H4ZM6 7h5M6 9.5h5M6 12h3',
  data: 'M8 2c3.3 0 6 1 6 2.3v7.4C14 13 11.3 14 8 14s-6-1-6-2.3V4.3C2 3 4.7 2 8 2ZM2 4.3C2 5.6 4.7 6.6 8 6.6s6-1 6-2.3',
  set: 'M8 5.6A2.4 2.4 0 1 0 8 10.4 2.4 2.4 0 0 0 8 5.6ZM8 1.6l.6 1.7 1.8-.6.9 1.6-1.3 1.3 1.3 1.3-.9 1.6-1.8-.6L8 14.4l-.6-1.7-1.8.6-.9-1.6 1.3-1.3-1.3-1.3.9-1.6 1.8.6Z',
}

export const NAV: (NavEntry | { group: string })[] = [
  { group: 'Workspace' },
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'projects', label: 'Projects', icon: 'folder' },
  { id: 'simulations', label: 'Simulations', icon: 'sim' },
  { group: 'Result domains' },
  { id: 'fea', label: 'FEA', icon: 'fea', domain: 'FEA' },
  { id: 'cfd', label: 'CFD', icon: 'cfd', domain: 'CFD' },
  { id: 'thermal', label: 'Thermal', icon: 'thermal', domain: 'Thermal' },
  { id: 'mbd', label: 'MBD', icon: 'mbd', domain: 'MBD' },
  { id: 'multiphysics', label: 'Modules', icon: 'multi' },
  { group: 'Analysis' },
  { id: 'comparison', label: 'Comparison', icon: 'cmp' },
  { id: 'validation', label: 'Validation', icon: 'val' },
  { id: 'diagnostics', label: 'Diagnostics', icon: 'diag' },
  { id: 'assistant', label: 'Engineering assistant', icon: 'ai' },
  { id: 'optimization', label: 'Optimization', icon: 'opt' },
  { group: 'Output' },
  { id: 'reports', label: 'Reports', icon: 'rep' },
  { id: 'data', label: 'Data & files', icon: 'data' },
  { id: 'settings', label: 'Settings', icon: 'set' },
]

export const DOMAIN_VIEW: Record<string, ViewId> = {
  FEA: 'fea', CFD: 'cfd', Thermal: 'thermal', MBD: 'mbd',
}
