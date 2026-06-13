"""Aegis CaseOps postmortem agent — UiPath coded agent entrypoint.

design.md O4 (deterministic baseline): formats M2 triage output + approval
history + remediation log into one markdown summary. This is the terminal
task for every branch. The Gaps section is ALWAYS rendered (不変量2/O5) —
an empty gap list is stated explicitly, never silently omitted.

The Analyst Assistant (M4) variant with Context Grounding citations may
replace this only if SPIKE-S5 passes; this agent stays as the fallback so
the submission never depends on the LLM path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class PostmortemIn:
    case_id: str
    triage_json: str
    approval_state: str = "not_required"  # approved | rejected | not_required
    ticket_id: str = ""
    remediation_log: list[str] = field(default_factory=list)


@dataclass
class PostmortemOut:
    postmortem_md: str


def main(input: PostmortemIn) -> PostmortemOut:
    try:
        triage = json.loads(input.triage_json)
    except (json.JSONDecodeError, TypeError):
        triage = {}
    if not isinstance(triage, dict):
        triage = {}

    evidence = [str(e) for e in triage.get("evidence", []) if isinstance(e, str)]
    gaps = [str(g) for g in triage.get("gaps", []) if isinstance(g, str)]

    lines = [
        f"# Postmortem: {input.case_id}",
        "",
        f"- severity: {triage.get('severity', 'unknown')}",
        f"- branch: {triage.get('maestro_branch', 'unknown')}",
        f"- confidence: {triage.get('confidence', 'unknown')}",
        f"- rationale: {triage.get('rationale', 'unavailable')}",
        "",
        "## Evidence",
        *([f"- {e}" for e in evidence] or ["- (none recorded)"]),
        "",
        "## Gaps (partial responses — reported, never hidden)",
        *([f"- {g}" for g in gaps] or ["- No gaps recorded for this case."]),
        "",
        "## Approval & Remediation",
        f"- approval: {input.approval_state}",
    ]
    if input.approval_state == "approved":
        lines.append(f"- ticket: {input.ticket_id or '(missing)'}")
        lines.extend(f"- {entry}" for entry in input.remediation_log)
    elif input.approval_state == "rejected":
        lines.append("- remediation: not executed (human rejected)")
    else:
        lines.append("- remediation: not applicable for this branch")

    return PostmortemOut(postmortem_md="\n".join(lines) + "\n")
