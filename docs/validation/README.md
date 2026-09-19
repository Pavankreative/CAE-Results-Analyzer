# Validation and diagnostics

Two separate mechanisms. **Validation** asks whether the result can be trusted, and returns a status
per check. **Diagnostics** describes what is notable in the data and what to look at next.

## Statuses

| Status | Meaning |
| --- | --- |
| `verified` | The check ran and passed on the data available |
| `warning` | The check ran and passed with a qualification |
| `investigate` | The check ran and failed |
| `not_validated` | The check could not run because the data it needs is not attached |

`not_validated` exists so that a missing mesh study or missing test data never reads as a pass.

## Checks (`analysis/validation.py`)

| Check | What it does |
| --- | --- |
| Unit consistency | Compares the declared units against the recognised consistent systems |
| Missing data | Counts non-finite entries in every field |
| Range and limit check | Compares each field against the `min_allowed`/`max_allowed` limits declared on it |
| Solver convergence | Compares the final residual monitors against the declared criterion |
| Mesh metadata | Checks that node and element metadata survived the import |
| Mesh convergence | Reads a refinement study from metadata; needs three levels to judge, reports the change over the last refinement against the acceptance band |
| Analytical comparison | Compares against an analytical or hand-calculation reference supplied with the case |
| Experimental comparison | Compares against test data supplied with the case |

Every check returns the evidence it used — the numbers, the limits and the source — and the UI shows
that evidence next to the status.

## Rules (`analysis/diagnostics.py`)

| Rule | Severity | Fires when |
| --- | --- | --- |
| `unit_consistency` | critical | The declared unit system is not consistent |
| `missing_data` | critical | A field contains NaN or infinite values |
| `limit_exceedance` | critical | A field exceeds its declared limit; reports how many entities are above it |
| `stress_concentration` | warning | The peak is more than twice the mean of its neighbourhood |
| `residual_plateau` | warning | A residual stays above the criterion and stops dropping over the final window |
| `monitor_stability` | info / warning | Reports the spread of an integrated monitor over the final window |
| `outlier` | info | The peak sits more than six standard deviations above the mean |

Each finding carries: title, severity, location (node id and coordinates where applicable), evidence,
possible cause and suggested investigation.

## What these do not do

- They do not certify a design. `limit_exceedance` compares a result against a limit recorded with
  the case; whether that limit is the right one for the application is outside the software.
- They cannot separate a genuine stress riser from a mesh singularity. The rule says so and points at
  the refinement study that would settle it.
- Calculations state their assumptions because those assumptions, not the arithmetic, are usually
  what makes a number wrong.
