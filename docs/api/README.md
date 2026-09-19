# HTTP API

Base path `/api`. Interactive documentation is served at `/docs` when the backend runs.

## Meta

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/health` | status, version, simulation and project counts |
| GET | `/adapters` | every adapter with `status: implemented \| planned` |
| GET | `/domains` | CAE domains with implementation status |

## Projects

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/projects` | list |
| POST | `/projects` | `{name, description?, owner?, simulation_ids?}` → 201; unknown simulation id → 404 |
| GET | `/projects/{id}` | project plus the summaries of its simulations |
| PUT | `/projects/{id}` | partial update |
| DELETE | `/projects/{id}` | 204 |

## Simulations

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/simulations?domain=CFD` | summaries, optional domain filter |
| GET | `/simulations/{id}` | detail: materials, BCs, loads, mesh metrics, bounds, convergence |
| GET | `/simulations/{id}/mesh` | flat `nodes` and `triangles` arrays ready for a WebGL buffer |
| GET | `/simulations/{id}/fields/{field}/values?step=-1` | values for one step plus min/max and limits |
| GET | `/simulations/{id}/fields/{field}/statistics?step=-1` | statistics, histogram and per-step envelope |
| GET | `/simulations/{id}/statistics` | statistics for every field |
| POST | `/simulations/{id}/filter` | `{field, step?, minimum?, maximum?, fraction_of_max?}` → selected indices and node ids |
| GET | `/simulations/{id}/calculations` | derived quantities with formula, inputs and assumptions |
| POST | `/simulations/{id}/derived-field` | `{kind: "safety_factor", source_field}` → adds a derived field |
| GET | `/simulations/{id}/validation` | all checks with evidence and an overall status |
| GET | `/simulations/{id}/diagnostics` | findings ordered by severity |
| DELETE | `/simulations/{id}` | 204; sample datasets are read-only and return 403 |

## Analysis and output

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/compare` | `{simulation_a, simulation_b, fields?, step?}` |
| POST | `/assistant/query` | `{simulation_id, question}` → labelled blocks, evidence and actions |
| GET | `/assistant/suggestions` | the questions the assistant can answer |
| GET | `/reports/sections` | available report sections and their titles |
| POST | `/reports` | `{simulation_id, sections?, compare_with?, format: markdown\|html\|json}` |
| POST | `/import` | multipart `file`, optional `?adapter=`; 201 with the simulation summary, 422 when no parser exists |

## Errors

| Status | Meaning |
| --- | --- |
| 400 | Bad request, e.g. a step outside the field's range |
| 403 | Attempt to delete a sample dataset |
| 404 | Unknown project, simulation or field |
| 413 | Upload above `CAER_MAX_UPLOAD_MB` |
| 422 | The file could not be parsed, or its format has only a planned adapter |

Every error body is `{"detail": "..."}` with a message intended to be shown to the user.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `CAER_DATA_DIR` | `<repo>/data` | Projects and imported simulations |
| `CAER_SAMPLES_DIR` | `<repo>/samples` | Read-only sample datasets |
| `CAER_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins |
| `CAER_LOG_LEVEL` | `INFO` | Logging level |
| `CAER_MAX_UPLOAD_MB` | `200` | Upload size limit |
