# Node-ID comparison verification — 2026-11-19

Base revision: `2e684041db98e93dd6374fecc808f2ea45c11063`.

## Defect and correction

The old comparator subtracted arrays by row position whenever node counts
matched. Permuting the supplied bracket's nodes, IDs, connectivity and results
with NumPy RNG seed 17 left the physical nodal solution unchanged but produced
an approximately 195.9621 MPa maximum absolute difference.

The corrected implementation aligns B's results to A by explicit Node ID and
rejects incompatible IDs, units, reference coordinates, fields and selected
steps. The same regression now returns **0.0 MPa maximum absolute difference
and 0.0 MPa RMS difference**. Independently prescribed signed changes of
`[3, -4, 0] MPa` retain their expected minimum, maximum, mean and RMS after
reordering.

Generated display IDs remain ineligible for comparison after native save/load.
Synthetic fixtures assign explicit reference IDs. Comparison and report API
validation errors return HTTP 422. A fresh sample-generation test also exposed
and corrected the CLI's inability to print output paths outside the repository.

## Execution record

- Python 3.12.14; NumPy 2.3.5; pytest 9.2.0.
- FastAPI 0.141.1; httpx 0.28.1.
- Baseline backend suite: **87 passed**.
- Updated backend suite: **124 passed**, including 37 additional regression cases.
- Latest full run: **9.86 seconds** on the execution host.
- Two pre-existing dependency deprecation warnings (AnyIO/pytest and
  Starlette/httpx); no test failures or skipped tests.
- `git diff --check`: passed.

From the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest -c backend/pytest.ini backend/tests -q
```

The regression suite regenerates all four samples into a temporary directory
and checks each resulting file. The execution host installed pytest in an
isolated dependency directory exposed through `PYTHONPATH`; this is an
environment detail, not a project requirement.

## Limits

This verifies the stated software cases. It does not certify solver results,
physical designs, imported legacy ID provenance, or every possible application
path. No proprietary solver runs or frontend build were performed for this
backend correction. Different meshes still need an explicit mapping workflow;
automatic interpolation and unit conversion are not implemented. Vector-field
differences are differences of magnitudes, as documented in the README.
