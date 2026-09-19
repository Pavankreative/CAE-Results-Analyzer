# The common CAE result model

Defined in `backend/app/core/model.py`. Every adapter produces these objects and every analysis
consumes them.

## Simulation

| Field | Meaning |
| --- | --- |
| `id`, `name` | Identity within the store |
| `domain` | `FEA`, `CFD`, `Thermal`, `MBD`, `Multiphysics`, `Electromagnetic`, `Battery`, `Acoustics`, `Manufacturing` |
| `analysis_type` | Free text, as the solver would describe the run |
| `solver` | Which code produced the result |
| `units` | `UnitSystem`, see below |
| `mesh` | `Mesh` |
| `fields` | `name -> ResultField` |
| `materials`, `boundary_conditions`, `loads` | Case setup, carried for reporting and calculations |
| `convergence` | `ConvergenceHistory` or `None` |
| `load_cases` | Names of the cases defined for the model; only the loaded one has data |
| `metadata` | Operating point, mesh refinement study, analytical and experimental references |
| `is_sample_data` | Drives the sample-data labelling in the UI and reports |

## Mesh

`nodes` is `(n_nodes, 3)`. `triangles` is `(n_tris, 3)` indexing into `nodes` — the render-ready
surface skin. `node_ids` keeps the solver's own numbering so an extremum can be reported as the node
the engineer would look up. `parts` and `part_ids` support per-part visibility. `elements` and
`metrics` carry whatever the adapter could read about the volume mesh.

Construction validates that no triangle references a node outside the array.

## ResultField

`values` has shape `(n_steps, n_entities)` for a scalar field and `(n_steps, n_entities, 3)` for a
vector field; a one-dimensional array is promoted to a single step. `step(i)` returns scalar values
for step `i`, taking the magnitude of a vector field.

| Field | Meaning |
| --- | --- |
| `location` | `nodal` or `elemental` |
| `field_type` | `scalar` or `vector` |
| `category` | Grouping used by the interface (Stress, Velocity, Wall, …) |
| `steps` | Step values: load fraction, iteration or time |
| `limits` | Declared limits, e.g. `{"yield": 276.0, "max_allowed": 276.0}` — the range check and the limit-exceedance rule read these |
| `derived` | True when the application computed the field rather than reading it |
| `provenance` | How a derived field was produced |

`Simulation.add_field` rejects a nodal field whose length does not match the node count, which is
what stops a mis-parsed file from becoming a plausible-looking result.

## Units

`UnitSystem` records length, mass, time, force, stress and temperature. `consistent` checks the set
against the recognised consistent systems (mm-kg-s-N-MPa, m-kg-s-N-Pa, in-lb-s-lbf-psi). Nothing is
auto-converted: a mismatch becomes a validation finding and a critical diagnostic, because silently
scaling someone's results is worse than refusing to.

## Interchange format

`NativeJSONAdapter` reads and writes `caer-result` version 1: a JSON document holding the structures
above with rounded arrays, optionally gzipped. It is what `samples/` ships and what the store writes
when a file is imported.
