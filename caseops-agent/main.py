"""Aegis CaseOps triage agent — UiPath coded agent entrypoint.

Deterministic core (design.md M1/M3): no LLM involvement in the verdict.
Ported from coded-agent/triage_agent.py; logic unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HIGH_RISK_ACTIONS = ["network_isolation", "privilege_revocation"]
MEDIUM_RISK_ACTIONS = ["analyst_review", "collect_more_evidence"]


@dataclass
class IncidentCaseIn:
    case_id: str
    asset: dict[str, Any] = field(default_factory=dict)
    signals: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    policy_context: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    title: str | None = None
    alert_time: str | None = None


@dataclass
class TriageOut:
    case_id: str
    severity: str
    confidence: float
    case_stage: str
    recommended_action: list[str]
    human_approval_required: bool
    maestro_branch: str
    evidence: list[str]
    gaps: list[str]
    rationale: str


def _risk_points(case: IncidentCaseIn) -> tuple[int, float, list[str], list[str]]:
    points = 0
    confidences: list[float] = []
    evidence: list[str] = []
    gaps: list[str] = []

    criticality = str(case.asset.get("criticality", "")).lower()
    if criticality == "high":
        points += 2
        evidence.append("critical asset")

    for signal in case.signals:
        if not isinstance(signal, dict):
            continue
        severity = int(signal.get("severity", 0) or 0)
        confidence = float(signal.get("confidence", 0) or 0)
        label = str(signal.get("label", "unnamed signal"))
        points += severity
        confidences.append(confidence)
        if severity >= 4:
            evidence.append(label)

    for tool_result in case.tool_results:
        if not isinstance(tool_result, dict):
            continue
        tool = str(tool_result.get("tool", "unknown_tool"))
        status = str(tool_result.get("status", "")).lower()
        summary = str(tool_result.get("summary", "")).strip()
        if status == "ok":
            evidence.append(f"{tool}: {summary}")
        else:
            gaps.append(f"{tool}: {summary or status or 'unavailable'}")
            points += 1

    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return points, avg_confidence, len(confidences), evidence, gaps


def _corroborated_confidence(avg: float, signal_count: int) -> float:
    # W7: confidence is monotone in corroboration. A single signal can never
    # assert more than 0.55; each additional independent signal lifts the
    # ceiling by 0.15 (4+ signals = uncapped).
    cap = 0.40 + 0.15 * signal_count
    return round(min(avg, cap), 2)


def main(input: IncidentCaseIn) -> TriageOut:
    points, avg_confidence, signal_count, evidence, gaps = _risk_points(input)
    confidence = _corroborated_confidence(avg_confidence, signal_count)

    if points >= 14:
        severity = "critical"
        case_stage = "human_approval"
        recommended_action = list(HIGH_RISK_ACTIONS)
        maestro_branch = "escalate_for_containment"
    elif points >= 9:
        severity = "high"
        case_stage = "human_approval"
        recommended_action = list(HIGH_RISK_ACTIONS)
        maestro_branch = "escalate_for_containment"
    elif points >= 5:
        severity = "medium"
        case_stage = "analyst_review"
        recommended_action = list(MEDIUM_RISK_ACTIONS)
        maestro_branch = "request_more_evidence"
    else:
        severity = "low"
        case_stage = "close_candidate"
        recommended_action = ["close_as_low_risk"]
        maestro_branch = "low_risk_close"

    human_approval_required = case_stage == "human_approval"
    if confidence < 0.7 and severity in {"high", "critical"}:
        recommended_action = ["analyst_review", *recommended_action]
        maestro_branch = "confidence_gap_review"

    rationale = (
        f"risk_points={points}; confidence={confidence}; signals={signal_count}; "
        f"evidence_count={len(evidence)}; gap_count={len(gaps)}"
    )

    return TriageOut(
        case_id=input.case_id,
        severity=severity,
        confidence=confidence,
        case_stage=case_stage,
        recommended_action=recommended_action,
        human_approval_required=human_approval_required,
        maestro_branch=maestro_branch,
        evidence=evidence,
        gaps=gaps,
        rationale=rationale,
    )
