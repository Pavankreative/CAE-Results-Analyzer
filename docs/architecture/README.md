# Architecture

## Layers

```text
frontend (React + TypeScript + Vite)
   │  fetch, JSON only
   ▼
api/        FastAPI routes, pydantic schemas, HTTP error mapping
services/   store (projects, simulations), assistant, report builder
analysis/   statistics · calculations · validation · diagnostics · comparison
adapters/   native JSON · VTK legacy · CSV · planned interfaces
core/       the common result model and runtime configuration
```

Each layer only depends on the ones below it. The analysis layer never imports an adapter, and no
adapter imports an analysis module.

## The import path

```text
CAE file
   ↓  registry.find_for(path)        pick an adapter by extension, preferring implemented ones
adapter.read(path)                   parse into the common model
   ↓  Simulation.add_field()         rejects fields whose length does not match the mesh
common result model
   ↓
analysis engines                     statistics, calculations, validation, diagnostics, comparison
   ↓
API responses / reports
```

A parser that cannot produce a valid `Simulation` raises instead of returning a partial one. The API
maps that to `422` with the adapter's message, so a rejected import is explained rather than silently
half-loaded.

## Why the boundary is at the adapter

Post-processing logic that knows about solver files ends up duplicated per format and untestable
without those files. Keeping format knowledge inside `adapters/` means:

- the analysis engines are tested against small synthetic models,
- adding a solver is one class plus one fixture,
- the application can state honestly, from the registry, which formats it reads.

## Storage

Projects are JSON documents under `data/projects/`. Simulations are native result files: read-only
sample datasets in `samples/`, imported ones in `data/simulations/`. The store caches parsed
simulations in memory because the value arrays are expensive to re-parse per request. There is no
database; a single-user desktop-style tool does not need one, and the file layout keeps results
diffable and portable.

## Frontend

`App.tsx` holds the navigation, the active simulation and a small toast channel, and passes an
`AppContext` down. Views fetch through `lib/api.ts` with the `useAsync` hook, which tracks
loading/error state and discards stale responses. The viewport is the only stateful component: it
owns the WebGL renderer, camera and geometry, and reacts to prop changes (field values, colour range,
clipping, part visibility) by updating buffers in place rather than rebuilding the scene.

## Deliberate non-goals for this version

- No solver execution, meshing or job submission.
- No authentication or multi-user state.
- No language model behind the assistant; the retrieval contract is in place for one to be added.
