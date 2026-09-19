# Contributing

## Ground rules

1. **Do not claim support that does not exist.** An adapter stays `planned` until it has a real
   parser and a test that reads a fixture file. The UI reads status from the registry, so changing a
   label without changing the code is not possible.
2. **Every number carries its provenance.** A calculation records its formula, inputs and
   assumptions; a validation check records the evidence behind its status; a diagnostic finding
   records what was observed and what to investigate. Code that returns a bare number will be asked
   for the rest.
3. **Analysis stays solver-independent.** Anything that knows about a file format belongs in
   `backend/app/adapters/`. Everything below that boundary sees only the common model.
4. **Interpretation is labelled.** The assistant separates simulation data, calculated values,
   engineering rules, interpretation and recommendation. Do not merge those categories.

## Development setup

```bash
pip install -r backend/requirements-dev.txt
python scripts/generate_samples.py
cd frontend && npm install
```

Run everything with `./scripts/dev.sh`, or the two servers separately (see the README).

## Before opening a pull request

```bash
cd backend && python -m pytest tests -q
cd ../frontend && npm run typecheck && npm test && npm run build
```

`tests/verify_install.sh` does all of it in one command.

## Adding an adapter

1. Subclass `BaseAdapter` in `backend/app/adapters/`, fill in `AdapterInfo` and implement `read()`
   returning a `Simulation`.
2. Register it in `backend/app/adapters/__init__.py`.
3. Add a small fixture under `samples/external/` and a test in `backend/tests/test_adapters.py`
   asserting node count, at least one field and its units.
4. Remove the matching entry from `planned.py` in the same commit.

## Adding a validation check or diagnostic rule

Add the function to `analysis/validation.py` or `analysis/diagnostics.py` and append it to `CHECKS`
or `RULES`. A check with no data to work on must return `NOT_VALIDATED` rather than a pass. A rule
must populate evidence, possible cause and suggested investigation.

## Style

Python: standard library plus numpy, type hints on public functions, no framework magic.
TypeScript: strict mode, no `any`, components stay presentational and fetch through `lib/api.ts`.
