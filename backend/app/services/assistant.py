"""Engineering assistant.

The assistant answers from the application's own structured data: statistics,
calculations, validation results and diagnostic findings. Every statement is
labelled by source type, and the evidence used is attached to the answer.

It does not call a language model and it does not invent numbers. An unmatched
question returns an honest "no stored answer" response listing what can be
asked. The architecture keeps the retrieval layer (context assembly) separate
from the wording layer, so a language model can be added later behind the same
contract without changing what counts as evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List, Optional

from app.analysis.calculations import standard_calculations
from app.analysis.diagnostics import run_diagnostics
from app.analysis.statistics import field_statistics
from app.analysis.validation import run_validation
from app.core.model import Simulation

# Block kinds, in the order they are presented.
DATA = "simulation_data"
CALC = "calculated"
RULE = "engineering_rule"
INTERP = "interpretation"
REC = "recommendation"

BLOCK_LABELS = {
    DATA: "Simulation data",
    CALC: "Calculated",
    RULE: "Engineering rule",
    INTERP: "Interpretation",
    REC: "Recommendation",
}


@dataclass
class Answer:
    question: str
    intent: str
    blocks: List[Dict[str, str]] = dc_field(default_factory=list)
    evidence: List[Dict[str, Any]] = dc_field(default_factory=list)
    actions: List[Dict[str, str]] = dc_field(default_factory=list)
    simulation_id: Optional[str] = None

    def add(self, kind: str, text: str) -> "Answer":
        self.blocks.append({"kind": kind, "label": BLOCK_LABELS[kind], "text": text})
        return self

    def ev(self, label: str, value: Any) -> "Answer":
        self.evidence.append({"label": label, "value": value})
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question, "intent": self.intent, "blocks": self.blocks,
            "evidence": self.evidence, "actions": self.actions,
            "simulation_id": self.simulation_id,
            "disclaimer": ("Answers are assembled from the stored result model. Interpretation "
                           "blocks are reasoning about that data, not a verified engineering "
                           "conclusion."),
        }


def _peak_field(sim: Simulation) -> Optional[str]:
    for n in ("von_mises", "stress", "temperature", "pressure", "joint_force", "displacement"):
        if n in sim.fields:
            return n
    return next(iter(sim.fields), None)


# ------------------------------------------------------------------- intents
def intent_maximum(sim: Simulation, q: str) -> Optional[Answer]:
    name = None
    for n, f in sim.fields.items():
        if n.replace("_", " ") in q or f.label.lower() in q:
            name = n
            break
    if name is None:
        if not any(w in q for w in ("maximum", "max", "peak", "highest", "where is")):
            return None
        name = _peak_field(sim)
    if name is None:
        return None
    st = field_statistics(sim, name)
    a = Answer(q, "maximum", simulation_id=sim.id)
    loc = (f"node {st.maximum.node_id} at ({', '.join(f'{c:.1f}' for c in st.maximum.coordinates)}) "
           f"{sim.units.length}" if st.maximum.coordinates else f"entity index {st.maximum.index}")
    a.add(DATA, f"Peak {st.label.lower()} in {sim.name} is {st.maximum.value:.4g} {st.unit} at {loc}. "
                f"The field mean is {st.mean:.4g} {st.unit} and P95 is {st.p95:.4g} {st.unit}.")
    fos = next((c for c in standard_calculations(sim) if c.name.startswith("Factor of safety")), None)
    if fos:
        a.add(CALC, f"{fos.formula} gives {fos.result:.3g} using the material data attached to this case.")
    a.add(RULE, "A peak that sits far above P95 is treated as suspect until it is shown to be "
                "mesh-converged, because sharp geometric features produce values that keep rising "
                "with refinement.")
    ratio = st.maximum.value / st.p95 if st.p95 else 1.0
    a.add(INTERP, f"The peak is {ratio:.2f} times the P95 value, which "
                  + ("suggests a strong local concentration." if ratio > 1.5
                     else "is consistent with a smooth field rather than a local spike."))
    a.add(REC, "Check the peak across refinement levels before using it as a design number, and "
               "compare a path-averaged value over the feature.")
    a.ev("field", st.label).ev("maximum", f"{st.maximum.value:.4g} {st.unit}")
    a.ev("node", st.maximum.node_id).ev("mean", f"{st.mean:.4g} {st.unit}")
    a.ev("P95", f"{st.p95:.4g} {st.unit}").ev("source", sim.source_file or sim.id)
    a.actions = [{"label": "Open the result", "target": "workspace",
                  "params": f"{sim.id}:{name}"}]
    return a


def intent_safety(sim: Simulation, q: str) -> Optional[Answer]:
    if not any(w in q for w in ("safety", "safe", "fos", "factor of safety", "margin")):
        return None
    calcs = [c for c in standard_calculations(sim) if "safety" in c.name.lower() or "ratio" in c.name.lower()]
    a = Answer(q, "safety", simulation_id=sim.id)
    if not calcs:
        a.add(DATA, f"{sim.name} does not carry the stress and material data needed for a "
                    "factor-of-safety calculation.")
        a.add(REC, "Attach a yield strength to the material, or select a structural simulation.")
        a.ev("fields available", len(sim.fields))
        a.ev("materials with a yield strength",
             sum(1 for m in sim.materials if "yield_strength" in m.properties))
        return a
    c = calcs[0]
    a.add(CALC, f"{c.name}: {c.formula} = {c.result:.3g} {c.unit}, from "
                + ", ".join(f"{i['name']} = {i['value']} {i['unit']}".strip() for i in c.inputs) + ".")
    a.add(RULE, "Whether that value is acceptable depends on the required margin for this component "
                "class, which is a programme requirement and is not held in the result model.")
    a.add(INTERP, ("No yielding is predicted at the peak location on this case."
                   if c.result > 1.0 else
                   "The peak exceeds the yield strength at the stated location on this case."))
    a.add(REC, f"Confirm the required minimum against the requirement owner. Assumptions in force: {c.assumptions}")
    for i in c.inputs:
        a.ev(i["name"], f"{i['value']} {i['unit']}".strip())
    a.actions = [{"label": "Open validation", "target": "validation", "params": sim.id}]
    return a


def intent_convergence(sim: Simulation, q: str) -> Optional[Answer]:
    if not any(w in q for w in ("converge", "convergence", "residual", "diverg")):
        return None
    a = Answer(q, "convergence", simulation_id=sim.id)
    c = sim.convergence
    if c is None:
        a.add(DATA, f"{sim.name} has no convergence history attached, so nothing can be said about "
                    "its convergence behaviour.")
        a.add(REC, "Import the solver monitor file to enable convergence checks.")
        a.ev("convergence history", "not attached")
        a.ev("analysis type", sim.analysis_type or sim.domain.value)
        return a
    finals = {k: v[-1] for k, v in c.monitors.items()}
    a.add(DATA, "Final monitor values: "
          + ", ".join(f"{k} = {v:.3g}" for k, v in finals.items())
          + f", over {len(c.iterations)} iterations"
          + (f", against a criterion of {c.criterion:.1e}." if c.criterion else "."))
    diag = run_diagnostics(sim)
    plateau = [f for f in diag["findings"] if f["rule"] == "residual_plateau"]
    stable = [f for f in diag["findings"] if f["rule"] == "monitor_stability"]
    if plateau:
        a.add(DATA, f"{len(plateau)} residual monitor(s) flatten above the criterion: "
                    + ", ".join(f["title"].split("'")[1] for f in plateau) + ".")
    a.add(RULE, "A residual plateau with stable integrated monitors points to local unsteadiness or "
                "limited cell quality rather than a failing solution; a diverging case moves the "
                "monitors as well.")
    if stable:
        a.add(INTERP, "Integrated monitors over the final window: "
              + "; ".join(f"{f['title'].split(chr(39))[1]} spread {f['evidence'][1]['value']}"
                          for f in stable if len(f["evidence"]) > 1) + ".")
    a.add(REC, "Check monitor stability over the same window as the plateau, inspect mesh quality "
               "where the residual is concentrated, and re-run unsteady for a short physical time "
               "if the wake or a separation region is suspected.")
    for k, v in finals.items():
        a.ev(f"final {k}", f"{v:.3g}")
    if c.criterion:
        a.ev("criterion", f"{c.criterion:.1e}")
    a.ev("iterations", len(c.iterations))
    a.actions = [{"label": "Open diagnostics", "target": "diagnostics", "params": sim.id}]
    return a


def intent_summary(sim: Simulation, q: str) -> Optional[Answer]:
    if not any(w in q for w in ("summar", "overview", "brief", "explain the results")):
        return None
    val = run_validation(sim)
    diag = run_diagnostics(sim)
    a = Answer(q, "summary", simulation_id=sim.id)
    peaks = []
    for name in list(sim.fields)[:5]:
        st = field_statistics(sim, name)
        peaks.append(f"{st.label} peaks at {st.maximum.value:.4g} {st.unit}")
    a.add(DATA, f"{sim.name} ({sim.domain.value}, {sim.analysis_type}, {sim.solver}): "
                + "; ".join(peaks) + ".")
    calcs = standard_calculations(sim)
    if calcs:
        a.add(CALC, "; ".join(f"{c.name} = {c.result:.4g} {c.unit}" for c in calcs if c.result == c.result) + ".")
    a.add(DATA, f"Validation is {val['overall'].replace('_', ' ')}; diagnostics report "
                f"{diag['counts']['critical']} critical, {diag['counts']['warning']} warning and "
                f"{diag['counts']['info']} information findings.")
    a.add(INTERP, ("A critical finding is open, so this case should not be signed off without "
                   "closing it." if diag["counts"]["critical"] else
                   "No critical finding is open; the remaining items limit how firmly the numbers "
                   "can be quoted rather than blocking the result."))
    a.add(REC, "Work through the diagnostics in severity order and record the closure of each item "
               "in the report before issuing it.")
    a.ev("validation", val["overall"]).ev("critical findings", diag["counts"]["critical"])
    a.ev("warnings", diag["counts"]["warning"]).ev("fields", len(sim.fields))
    a.actions = [{"label": "Build a report", "target": "reports", "params": sim.id}]
    return a


def intent_compare(sim: Simulation, q: str) -> Optional[Answer]:
    if not any(w in q for w in ("compare", "versus", " vs ", "difference between")):
        return None
    a = Answer(q, "compare", simulation_id=sim.id)
    a.add(DATA, "Comparison runs over two selected simulations and reports scalar deltas, "
                "percentage differences, pointwise field differences when the meshes match, and "
                "overlaid histories.")
    a.add(RULE, "A comparison is only attributable to the design change when solver version, mesh "
                "family and load definition are otherwise identical.")
    a.add(REC, "Open the comparison view and select simulation A and B; the response there is "
               "computed from both result sets rather than from stored text.")
    a.ev("this simulation", f"{sim.id} ({sim.domain.value})")
    a.ev("comparable fields", len(sim.fields))
    a.ev("endpoint", "POST /api/compare")
    a.actions = [{"label": "Open comparison", "target": "comparison", "params": sim.id}]
    return a


def intent_filter(sim: Simulation, q: str) -> Optional[Answer]:
    if not any(w in q for w in ("above", "regions", "threshold", "% of", "percent of")):
        return None
    import re
    m = re.search(r"(\d{1,3})\s*%", q)
    frac = (int(m.group(1)) / 100.0) if m else 0.8
    name = _peak_field(sim)
    if name is None:
        return None
    from app.analysis.statistics import filter_field
    res = filter_field(sim, name, fraction_of_max=frac)
    st = field_statistics(sim, name)
    a = Answer(q, "filter", simulation_id=sim.id)
    threshold = st.maximum.value * frac
    a.add(DATA, f"{int(frac * 100)} % of the peak {st.label.lower()} is {threshold:.4g} {st.unit}. "
                f"{res['selected']} of {res['total']} nodes ({res['fraction'] * 100:.2f} %) are at "
                f"or above that value.")
    yield_strength = sim.field(name).limits.get("yield")
    if yield_strength:
        a.add(CALC, f"Against the declared yield strength of {yield_strength:.4g} {st.unit}, "
                    f"{int(frac * 100)} % of yield is {yield_strength * frac:.4g} {st.unit} and the "
                    f"peak reaches {st.maximum.value / yield_strength * 100:.1f} % of yield.")
    a.add(REC, "Apply the same threshold in the viewport filter to see where those entities are, "
               "and repeat for the other load cases in the project.")
    a.ev("threshold", f"{threshold:.4g} {st.unit}").ev("entities selected", res["selected"])
    a.ev("share of model", f"{res['fraction'] * 100:.2f} %")
    a.actions = [{"label": "Filter the viewport", "target": "filter",
                  "params": f"{sim.id}:{name}:{frac}"}]
    return a


INTENTS: List[Callable[[Simulation, str], Optional[Answer]]] = [
    intent_filter, intent_safety, intent_convergence, intent_summary,
    intent_compare, intent_maximum,
]

SUGGESTIONS = [
    "Where is maximum stress?",
    "What is the factor of safety?",
    "Show regions above 80% of the peak",
    "Why might convergence be poor?",
    "Summarize the results",
    "Compare these simulations",
]


def ask(sim: Simulation, question: str) -> Dict[str, Any]:
    q = question.lower().strip()
    for intent in INTENTS:
        answer = intent(sim, q)
        if answer is not None:
            return answer.to_dict()
    a = Answer(question, "unmatched", simulation_id=sim.id)
    a.add(DATA, f"No stored answer matches that question. {sim.name} holds "
                f"{len(sim.fields)} result fields: "
                + ", ".join(f.label for f in sim.fields.values()) + ".")
    a.add(REC, "Try one of: " + "; ".join(SUGGESTIONS) + ".")
    a.ev("fields available", len(sim.fields))
    return a.to_dict()
