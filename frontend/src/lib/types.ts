export type ValidationStatus = 'verified' | 'warning' | 'investigate' | 'not_validated'
export type Severity = 'critical' | 'warning' | 'info'

export interface FieldSummary {
  name: string
  label: string
  unit: string
  category: string
  steps: number
  derived: boolean
  type: 'scalar' | 'vector'
  location: 'nodal' | 'elemental'
}

export interface SimulationSummary {
  id: string
  name: string
  domain: string
  analysis_type: string
  solver: string
  units: Record<string, string>
  nodes: number
  triangles: number
  fields: FieldSummary[]
  load_cases: string[]
  is_sample_data: boolean
  source_file: string
  adapter: string
  metadata: Record<string, unknown>
}

export interface SimulationDetail extends SimulationSummary {
  project_id: string | null
  materials: Record<string, unknown>[]
  boundary_conditions: { name: string; kind: string; definition: string }[]
  loads: { name: string; definition: string }[]
  mesh_metrics: Record<string, unknown>
  bounds: { min: number[]; max: number[] }
  parts: string[]
  convergence: {
    iterations: number[]
    monitors: Record<string, number[]>
    criterion: number | null
    converged: boolean | null
  } | null
}

export interface MeshPayload {
  nodes: number[]
  triangles: number[]
  node_count: number
  triangle_count: number
  parts: string[]
  part_ids: number[]
  bounds: { min: number[]; max: number[] }
}

export interface FieldValues {
  field: string
  label: string
  unit: string
  step: number
  steps: number[]
  values: number[]
  min: number
  max: number
  limits: Record<string, number>
  derived: boolean
}

export interface Extremum {
  value: number
  index: number
  node_id: number | null
  coordinates: number[] | null
}

export interface FieldStatistics {
  field: string
  label: string
  unit: string
  step: number
  count: number
  minimum: Extremum
  maximum: Extremum
  mean: number
  std: number
  median: number
  p95: number
  p99: number
  nan_count: number
  histogram?: { counts: number[]; edges: number[] }
  envelope?: { steps: number[]; min: number[]; max: number[]; mean: number[] }
}

export interface Evidence {
  label: string
  value: string | number
}

export interface ValidationCheck {
  name: string
  status: ValidationStatus
  message: string
  evidence: Evidence[]
}

export interface ValidationReport {
  simulation_id: string
  overall: ValidationStatus
  counts: Record<string, number>
  checks: ValidationCheck[]
}

export interface Finding {
  title: string
  severity: Severity
  location: string
  evidence: Evidence[]
  possible_cause: string
  suggested_investigation: string
  rule: string
}

export interface DiagnosticsReport {
  simulation_id: string
  counts: Record<Severity, number>
  findings: Finding[]
}

export interface Calculation {
  name: string
  formula: string
  inputs: { name: string; value: string | number; unit: string }[]
  result: number
  unit: string
  assumptions: string
  category: string
  note: string
}

export interface Project {
  id: string
  name: string
  description: string
  owner: string
  created: string
  modified: string
  simulation_ids: string[]
  metadata: Record<string, unknown>
  simulations?: SimulationSummary[]
}

export interface AssistantBlock {
  kind: string
  label: string
  text: string
}

export interface AssistantAnswer {
  question: string
  intent: string
  blocks: AssistantBlock[]
  evidence: Evidence[]
  actions: { label: string; target: string; params: string }[]
  simulation_id: string | null
  disclaimer: string
}

export interface ComparisonScalar {
  field: string
  label: string
  metric: string
  unit: string
  a: number
  b: number
  delta: number
  percent: number | null
}

export interface Comparison {
  a: { id: string; name: string; solver: string; analysis_type: string }
  b: { id: string; name: string; solver: string; analysis_type: string }
  shared_fields: string[]
  same_mesh: boolean
  mesh_note: string
  scalars: ComparisonScalar[]
  field_differences: {
    field: string; unit: string; min: number; max: number
    mean: number; abs_max: number; rms: number
  }[]
  overlays: {
    field: string; unit: string
    a: { steps: number[]; values: number[] }
    b: { steps: number[]; values: number[] }
  }[]
  calculations: { name: string; unit: string; a: number; b: number; delta: number; percent: number | null }[]
}

export interface AdapterInfo {
  key: string
  name: string
  solver: string
  extensions: string[]
  status: 'implemented' | 'planned'
  notes: string
}
