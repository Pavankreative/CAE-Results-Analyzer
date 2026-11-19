# User guide

## Getting in

Start the backend and the frontend (see the README), then open `http://localhost:5173`. The four
sample datasets load automatically and each gets a project. The banner in the status bar and the
flag in the viewport are there to make it obvious that this is sample data.

## Home

Counts across the workspace, the loaded simulations with their validation state, and every critical
or warning finding. Selecting a row opens that result in its domain workspace.

## Projects

Create a project, attach simulations to it, open or delete it. Projects are JSON files under
`data/projects/`, so they survive a restart and can be committed or shared.

## Simulations

Every result set currently mapped into the common model, with its solver, analysis type, node count,
field count and the adapter that read it.

## The workspace (FEA / CFD / Thermal / MBD)

```text
Project tree │ 3D result viewport │ Analysis & properties
             │                    │
             └── Plots · statistics · calculations · diagnostics · validation ──┘
```

- **Project tree** — geometry parts (click to hide or show), mesh metrics, materials, boundary
  conditions, loads, simulation cases and the result fields grouped by category. Click a field to
  display it.
- **Viewport** — drag to orbit, shift-drag or right-drag to pan, wheel to zoom. Hovering reads the
  value at the nearest node; clicking places a probe that is listed in the properties panel. The
  toolbar has view presets, wireframe, transparency, a section plane and probe clearing. The
  timeline at the bottom steps or plays through the solution steps.
- **Legend** — variable, unit, the active range and the colour map, so a screenshot is readable on
  its own.
- **Properties tabs** — *Properties* (case data, active result, probes, materials), *Results*
  (variable picker, derived-field creation), *Filters* (range sliders, threshold selection, section
  plane, part visibility), *Controls* (deformation scale, display toggles, view presets, validation
  summary).
- **Dock tabs** — *Plots* (step envelope, residual history, monitors), *Statistics* (full statistics
  and the distribution), *Calculations* (each with formula, inputs, result and assumptions),
  *Diagnostics*, *Validation*.

## Comparison

Pick compatible simulations A and B. Results are B minus A after explicit Node-ID
alignment, never row-index subtraction. Both datasets must have unique, explicit
Node IDs with identical sets, matching reference coordinates and units, and
compatible nodal fields and selected steps. Invalid comparisons return a specific
validation error instead of partial or scalar-only output. Vector fields compare
magnitudes. Different meshes require an explicit mapping workflow, which is not
implemented. See the root README for tolerances and regression-test commands.

## Validation

Every check for every simulation with its status and the evidence behind it. Four states: verified,
passed with warnings, requires investigation, not validated. A check with nothing to work on stays
*not validated* — it never defaults to a pass.

## Diagnostics

Findings from every simulation, filterable by severity. Each expands to evidence, location, possible
cause and suggested investigation. The findings describe what the data shows and what to check next;
they do not declare a design acceptable.

## Engineering assistant

Ask about the active simulation. Answers are assembled from the application's own data and each
block is labelled: simulation data, calculated, engineering rule, interpretation, recommendation. The
evidence used is attached, and action buttons jump to the relevant view — including applying a
threshold filter to the viewport. A question outside the supported intents gets an explicit "no
stored answer" rather than an invented one.

## Modules

Which domains and which file formats are implemented and which are registered as planned. Read from
the backend registry.

## Reports

Choose sections, optionally a second simulation for a comparison section, then generate Markdown
(previewed and downloadable) or HTML (opens in a tab). Reports built from sample data say so in the
body.

## Data & files

Drop a `.vtk`, `.csv` or native `.json` result to import it. The log shows what the adapter produced
or why the file was rejected. The two tables list implemented formats and planned ones with what a
parser for each would need.

## Settings

Theme, and the backend connection state.
