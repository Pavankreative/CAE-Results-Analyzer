"""Structured engineering report generation.

The report is built as data first, then rendered. Markdown, HTML and JSON
exports are implemented; each renders the same structure.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.analysis.calculations import standard_calculations
from app.analysis.comparison import compare
from app.analysis.diagnostics import run_diagnostics
from app.analysis.statistics import field_statistics
from app.analysis.validation import run_validation
from app.core.model import Project, Simulation

SECTIONS = [
    "project", "simulation", "solver", "mesh", "materials", "boundary_conditions",
    "loads", "convergence", "results", "calculations", "validation", "diagnostics",
    "comparison", "conclusions", "appendix",
]

SECTION_TITLES = {
    "project": "Project", "simulation": "Simulation", "solver": "Solver",
    "mesh": "Mesh", "materials": "Materials", "boundary_conditions": "Boundary conditions",
    "loads": "Loads", "convergence": "Convergence", "results": "Results",
    "calculations": "Engineering calculations", "validation": "Validation",
    "diagnostics": "Diagnostics", "comparison": "Comparison",
    "conclusions": "Conclusions", "appendix": "Appendix",
}


def build_report(sim: Simulation, project: Optional[Project] = None,
                 sections: Optional[List[str]] = None,
                 compare_with: Optional[Simulation] = None) -> Dict[str, Any]:
    wanted = [s for s in (sections or SECTIONS) if s in SECTIONS]
    val = run_validation(sim)
    diag = run_diagnostics(sim)
    calcs = [c.to_dict() for c in standard_calculations(sim)]
    stats = []
    for name in sim.fields:
        try:
            st = field_statistics(sim, name)
        except ValueError:
            continue
        stats.append({
            "label": st.label, "unit": st.unit,
            "min": round(st.minimum.value, 6), "max": round(st.maximum.value, 6),
            "mean": round(st.mean, 6), "std": round(st.std, 6),
            "max_node": st.maximum.node_id,
            "max_location": st.maximum.coordinates,
        })

    body: Dict[str, Any] = {}
    for s in wanted:
        if s == "project":
            body[s] = (project.to_dict() if project else
                       {"name": "(standalone simulation)", "id": "-", "description": ""})
        elif s == "simulation":
            body[s] = {"id": sim.id, "name": sim.name, "domain": sim.domain.value,
                       "analysis_type": sim.analysis_type, "load_cases": sim.load_cases,
                       "units": sim.units.to_dict(), "is_sample_data": sim.is_sample_data}
        elif s == "solver":
            body[s] = {"solver": sim.solver, "source_file": sim.source_file,
                       "adapter": sim.adapter, **{k: v for k, v in sim.metadata.items()
                                                  if k in ("run", "wall_time", "owner")}}
        elif s == "mesh":
            body[s] = {**sim.mesh.metrics, "Surface triangles": sim.mesh.n_triangles,
                       "Bounds": sim.mesh.bounds()}
        elif s == "materials":
            body[s] = [{"name": m.name, **m.properties} for m in sim.materials]
        elif s == "boundary_conditions":
            body[s] = [{"name": b.name, "kind": b.kind, "definition": b.definition}
                       for b in sim.boundary_conditions]
        elif s == "loads":
            body[s] = [{"name": l.name, "definition": l.definition} for l in sim.loads]
        elif s == "convergence":
            body[s] = ({"iterations": len(sim.convergence.iterations),
                        "criterion": sim.convergence.criterion,
                        "final": {k: v[-1] for k, v in sim.convergence.monitors.items()}}
                       if sim.convergence else {"note": "No convergence history attached."})
        elif s == "results":
            body[s] = stats
        elif s == "calculations":
            body[s] = calcs
        elif s == "validation":
            body[s] = val
        elif s == "diagnostics":
            body[s] = diag
        elif s == "comparison":
            body[s] = (compare(sim, compare_with) if compare_with else
                       {"note": "No second simulation was selected for comparison."})
        elif s == "conclusions":
            body[s] = {
                "validation_state": val["overall"],
                "critical_findings": diag["counts"]["critical"],
                "warnings": diag["counts"]["warning"],
                "statements": [f"{x['label']} reaches {x['max']:.4g} {x['unit']}" for x in stats[:6]],
                "open_actions": [f["suggested_investigation"] for f in diag["findings"]
                                 if f["severity"] in ("critical", "warning")],
            }
        elif s == "appendix":
            body[s] = {"fields": [{"name": f.name, "label": f.label, "unit": f.unit,
                                   "steps": f.n_steps, "derived": f.derived,
                                   "provenance": f.provenance} for f in sim.fields.values()],
                       "adapters_note": "Result imported through the "
                                        f"'{sim.adapter or 'native-json'}' adapter."}
    return {
        "title": f"{sim.name} - engineering report",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "sample_data": sim.is_sample_data,
        "sections": wanted,
        "body": body,
    }


# ------------------------------------------------------------------ rendering
def _kv_md(d: Dict[str, Any]) -> str:
    rows = ["| Item | Value |", "| --- | --- |"]
    for k, v in d.items():
        rows.append(f"| {k} | {v} |")
    return "\n".join(rows)


def _rows_md(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "_None recorded._"
    keys = list(items[0].keys())
    out = ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    for it in items:
        out.append("| " + " | ".join(str(it.get(k, "")) for k in keys) + " |")
    return "\n".join(out)


def to_markdown(report: Dict[str, Any]) -> str:
    out = [f"# {report['title']}", "", f"_Generated {report['generated']}._", ""]
    if report["sample_data"]:
        out += ["> **Sample data.** This report was generated from a demonstration dataset "
                "and is not suitable for design release.", ""]
    for i, s in enumerate(report["sections"], 1):
        data = report["body"][s]
        out.append(f"## {i} {SECTION_TITLES[s]}")
        if s == "calculations":
            for c in data:
                out += [f"**{c['name']}**", "", f"`{c['formula']}`", "",
                        ", ".join(f"{x['name']} = {x['value']} {x['unit']}".strip() for x in c["inputs"]),
                        "", f"Result: **{c['result']} {c['unit']}**", "",
                        f"_Assumptions: {c['assumptions']}_", ""]
        elif s == "validation":
            out += [f"Overall: **{data['overall'].replace('_', ' ')}**", ""]
            for c in data["checks"]:
                ev = "; ".join(f"{e['label']} {e['value']}" for e in c["evidence"][:8])
                out += [f"- **{c['name']}** - {c['status'].replace('_',' ')}: {c['message']}",
                        f"  - Evidence: {ev or 'none'}"]
            out.append("")
        elif s == "diagnostics":
            if not data["findings"]:
                out += ["No findings.", ""]
            for f in data["findings"]:
                ev = "; ".join(f"{e['label']} {e['value']}" for e in f["evidence"])
                out += [f"- **{f['title']}** ({f['severity']}) at {f['location']}",
                        f"  - Evidence: {ev}", f"  - Possible cause: {f['possible_cause']}",
                        f"  - Suggested investigation: {f['suggested_investigation']}"]
            out.append("")
        elif isinstance(data, list):
            out += [_rows_md(data), ""]
        elif isinstance(data, dict):
            out += [_kv_md({k: v for k, v in data.items() if not isinstance(v, (list, dict))}), ""]
            for k, v in data.items():
                if isinstance(v, list) and v and isinstance(v[0], (str, int, float)):
                    out += [f"**{k}**", ""] + [f"- {x}" for x in v] + [""]
        else:
            out += [str(data), ""]
    return "\n".join(out)


def to_html(report: Dict[str, Any]) -> str:
    md = to_markdown(report)
    body_lines = []
    in_table = False
    for line in md.splitlines():
        if line.startswith("| "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("- "):
                continue
            if not in_table:
                body_lines.append("<table>")
                in_table = True
                body_lines.append("<tr>" + "".join(f"<th>{_html.escape(c)}</th>" for c in cells) + "</tr>")
                continue
            body_lines.append("<tr>" + "".join(f"<td>{_html.escape(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            body_lines.append("</table>")
            in_table = False
        if line.startswith("## "):
            body_lines.append(f"<h2>{_html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            body_lines.append(f"<h1>{_html.escape(line[2:])}</h1>")
        elif line.startswith("> "):
            body_lines.append(f"<blockquote>{_html.escape(line[2:])}</blockquote>")
        elif line.startswith("- "):
            body_lines.append(f"<li>{_html.escape(line[2:])}</li>")
        elif line.strip():
            body_lines.append(f"<p>{_html.escape(line)}</p>")
    if in_table:
        body_lines.append("</table>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{_html.escape(report['title'])}</title>
<style>
 body{{font:14px/1.5 'IBM Plex Sans',system-ui,sans-serif;color:#16222b;max-width:900px;margin:40px auto;padding:0 24px}}
 h1{{font-size:22px;margin-bottom:4px}} h2{{font-size:15px;margin:26px 0 8px;border-bottom:1px solid #ccd6de;padding-bottom:4px}}
 table{{border-collapse:collapse;width:100%;margin:8px 0;font-size:12.5px}}
 th,td{{border:1px solid #ccd6de;padding:5px 8px;text-align:left}} th{{background:#eef1f4}}
 blockquote{{border-left:3px solid #a9631a;margin:0;padding:6px 12px;background:#fdf6ec}}
 code{{font-family:'IBM Plex Mono',monospace;background:#eef1f4;padding:1px 4px}}
 li{{margin:2px 0}}
</style></head><body>
{chr(10).join(body_lines)}
</body></html>"""


RENDERERS = {"markdown": to_markdown, "html": to_html}
