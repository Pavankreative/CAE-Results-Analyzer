import type {
  AdapterInfo, AssistantAnswer, Calculation, Comparison, DiagnosticsReport,
  FieldStatistics, FieldValues, MeshPayload, Project, SimulationDetail,
  SimulationSummary, ValidationReport,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the backend. Start it with: uvicorn app.main:app --reload')
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* response had no JSON body */ }
    throw new ApiError(res.status, detail)
  }
  const type = res.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? res.json() : res.text()) as Promise<T>
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: () => request<{ status: string; version: string; simulations: number }>('/health'),
  adapters: () => request<{ adapters: AdapterInfo[]; implemented: string[]; note: string }>('/adapters'),
  domains: () => request<{ domains: { key: string; status: string }[] }>('/domains'),

  projects: () => request<Project[]>('/projects'),
  project: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (body: Partial<Project>) => post<Project>('/projects', body),
  updateProject: (id: string, body: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),

  simulations: (domain?: string) =>
    request<SimulationSummary[]>(`/simulations${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`),
  simulation: (id: string) => request<SimulationDetail>(`/simulations/${id}`),
  mesh: (id: string) => request<MeshPayload>(`/simulations/${id}/mesh`),
  fieldValues: (id: string, field: string, step = -1) =>
    request<FieldValues>(`/simulations/${id}/fields/${field}/values?step=${step}`),
  fieldStatistics: (id: string, field: string, step = -1) =>
    request<FieldStatistics>(`/simulations/${id}/fields/${field}/statistics?step=${step}`),
  filter: (id: string, body: { field: string; step?: number; minimum?: number; maximum?: number; fraction_of_max?: number }) =>
    post<{ selected: number; total: number; fraction: number; node_ids: number[]; lower: number | null; upper: number | null }>(
      `/simulations/${id}/filter`, body),
  calculations: (id: string) => request<Calculation[]>(`/simulations/${id}/calculations`),
  derivedField: (id: string, source_field: string) =>
    post<{ created: string; label: string; provenance: string }>(`/simulations/${id}/derived-field`,
      { kind: 'safety_factor', source_field }),
  validation: (id: string) => request<ValidationReport>(`/simulations/${id}/validation`),
  diagnostics: (id: string) => request<DiagnosticsReport>(`/simulations/${id}/diagnostics`),

  compare: (a: string, b: string, fields?: string[]) =>
    post<Comparison>('/compare', { simulation_a: a, simulation_b: b, fields }),
  ask: (simulation_id: string, question: string) =>
    post<AssistantAnswer>('/assistant/query', { simulation_id, question }),
  suggestions: () => request<{ suggestions: string[]; block_kinds: Record<string, string> }>('/assistant/suggestions'),

  reportSections: () => request<{ sections: string[]; titles: Record<string, string> }>('/reports/sections'),
  report: (body: { simulation_id: string; sections?: string[]; format?: string; compare_with?: string }) =>
    post<string>('/reports', { format: 'markdown', ...body }),

  importFile: async (file: File): Promise<SimulationSummary> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/import`, { method: 'POST', body: form })
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new ApiError(res.status, body.detail ?? 'import failed')
    }
    return res.json()
  },
}
