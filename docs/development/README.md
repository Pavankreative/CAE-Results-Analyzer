# Development

## Environment

```bash
pip install -r backend/requirements-dev.txt
python scripts/generate_samples.py
cd frontend && npm install
```

Run both servers with `./scripts/dev.sh`, or separately:

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

The Vite dev server proxies `/api` to `127.0.0.1:8000`; override with `CAER_API_URL`.

## Layout

| Path | Contents |
| --- | --- |
| `backend/app/core/` | result model, settings |
| `backend/app/adapters/` | one module per format, plus the registry |
| `backend/app/analysis/` | statistics, calculations, validation, diagnostics, comparison |
| `backend/app/services/` | store, assistant, reports |
| `backend/app/api/` | routes and schemas |
| `frontend/src/lib/` | API client, types, colour maps, formatting, hooks |
| `frontend/src/components/` | viewport, legend, plot, finding card, primitives |
| `frontend/src/views/` | one module per navigation entry |
| `scripts/` | sample generator, procedural mesh helpers, dev launcher |

## Adding an adapter

```python
class MyFormatAdapter(BaseAdapter):
    info = AdapterInfo(key="my-format", name="My format", solver="My Solver",
                       extensions=[".myf"], status="implemented",
                       notes="What it reads.")

    def read(self, path: Path, **kwargs) -> Simulation:
        ...  # build Mesh, Simulation, ResultField objects
```

Register it in `adapters/__init__.py`, drop a fixture in `samples/external/`, add a test, and delete
the corresponding entry from `planned.py`. Status must not change without a parser behind it.

## Adding an analysis

Statistics and filters live in `analysis/statistics.py` and take `(Simulation, field_name, step)`.
Derived quantities return a `Calculation` carrying formula, inputs, result, unit and assumptions —
the UI renders those fields directly, so a calculation without them will look broken, which is
intentional.

Register a new domain default in `standard_calculations()` and guard the inputs: a missing input
produces an "Incomplete input" entry rather than a guessed value.

## Adding a view

Create `frontend/src/views/MyView.tsx` taking `{ ctx }: { ctx: AppContext }`, add an entry to
`lib/nav.ts` and a case in the `views` record in `App.tsx`. Fetch with `useAsync` so loading and
error states are handled consistently, and render errors with `<ErrorNote />`.

## Sample data

`scripts/generate_samples.py` builds the four datasets from the procedural surface meshes in
`scripts/geometry.py` and writes them through the native adapter. The random seed is fixed, so
regenerating gives byte-identical files and the tests that assert specific peaks keep passing. If you
change a field construction, re-run the generator and update any test that pinned a value.

## Testing

```bash
cd backend && python -m pytest tests -q          # 87 tests
cd frontend && npm run typecheck && npm test && npm run build
./tests/verify_install.sh                        # everything, as CI runs it
```

Backend fixtures in `backend/tests/conftest.py` build a store on a temporary data directory pointed
at the real `samples/`, so tests read the same datasets a user does.

## Conventions

- Python: type hints on public functions; numpy for arrays; no implicit unit conversion anywhere.
- TypeScript: strict mode, no `any`, view components fetch only through `lib/api.ts`.
- Errors the user can act on are raised with a message written for them, not for a log.
