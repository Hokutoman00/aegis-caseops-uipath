"""Regression tests: 3 demo fixtures + design.md invariants (§3)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import IncidentCaseIn, main

DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"

REQUIRED_INPUT_KEYS = {"case_id", "asset", "signals", "tool_results", "policy_context"}


def load_case(name: str) -> IncidentCaseIn:
    raw = json.loads((DEMO_DATA / name).read_text(encoding="utf-8"))
    return IncidentCaseIn(**raw)


def raw_gap_tools(case: IncidentCaseIn) -> list[str]:
    return [
        str(t.get("tool"))
        for t in case.tool_results
        if str(t.get("status", "")).lower() != "ok"
    ]


# --- D1: low-risk auto close -------------------------------------------------

def test_d1_low_risk_close():
    out = main(load_case("incident-case-002-low.json"))
    assert out.severity == "low"
    assert out.maestro_branch == "low_risk_close"
    assert out.case_stage == "close_candidate"
    assert out.human_approval_required is False
    # avg=0.93 but only 2 signals -> corroboration cap 0.40 + 0.15*2 = 0.70
    assert out.confidence == 0.7
    assert out.gaps == []
    assert out.rationale == "risk_points=2; confidence=0.7; signals=2; evidence_count=3; gap_count=0"


# --- D2: critical escalation (M2 fixture exact match) ------------------------

def test_d2_escalate_matches_m2_fixture():
    out = main(load_case("incident-case-001.json"))
    assert out.severity == "critical"
    assert out.maestro_branch == "escalate_for_containment"
    assert out.human_approval_required is True
    assert out.confidence == 0.76
    assert out.recommended_action == ["network_isolation", "privilege_revocation"]
    assert out.gaps == ["asset_inventory: Inventory API timed out."]
    assert len(out.evidence) == 5
    assert out.rationale == "risk_points=15; confidence=0.76; signals=3; evidence_count=5; gap_count=1"


# --- D3: confidence gap review ------------------------------------------------

def test_d3_confidence_gap_review():
    out = main(load_case("incident-case-003-gap.json"))
    assert out.severity == "high"
    assert out.maestro_branch == "confidence_gap_review"
    assert out.confidence == 0.57
    assert out.recommended_action[0] == "analyst_review"
    assert out.human_approval_required is True
    assert len(out.gaps) == 2
    assert out.rationale == "risk_points=12; confidence=0.57; signals=2; evidence_count=4; gap_count=2"


# --- Invariants (design.md §3) -------------------------------------------------

ALL_FIXTURES = [
    "incident-case-001.json",
    "incident-case-002-low.json",
    "incident-case-003-gap.json",
]


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_invariant_2_gaps_propagate_untouched(name):
    case = load_case(name)
    out = main(case)
    failed_tools = raw_gap_tools(case)
    assert len(out.gaps) == len(failed_tools)
    for tool, gap in zip(failed_tools, out.gaps):
        assert gap.startswith(f"{tool}: ")


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_invariant_1_high_risk_actions_imply_approval(name):
    out = main(load_case(name))
    if set(out.recommended_action) & {"network_isolation", "privilege_revocation"}:
        assert out.human_approval_required is True


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_invariant_4_shared_input_schema(name):
    raw = json.loads((DEMO_DATA / name).read_text(encoding="utf-8"))
    assert REQUIRED_INPUT_KEYS <= set(raw)
    for signal in raw["signals"]:
        assert {"type", "label", "severity", "confidence"} <= set(signal)
    for tool_result in raw["tool_results"]:
        assert {"tool", "status", "summary"} <= set(tool_result)


def test_invariant_1_negative_low_never_requires_approval():
    out = main(load_case("incident-case-002-low.json"))
    assert not (set(out.recommended_action) & {"network_isolation", "privilege_revocation"})
    assert out.human_approval_required is False


# --- W7: corroboration cap ------------------------------------------------------

def synthetic_case(severities: list[int], signal_confidence: float = 0.9,
                   criticality: str = "low", failed_tools: int = 0) -> IncidentCaseIn:
    return IncidentCaseIn(
        case_id="SYN-0001",
        asset={"criticality": criticality},
        signals=[
            {"type": "t", "label": f"s{i}", "severity": s, "confidence": signal_confidence}
            for i, s in enumerate(severities)
        ],
        tool_results=[
            {"tool": f"tool{i}", "status": "failed", "summary": "down"}
            for i in range(failed_tools)
        ],
        policy_context={},
    )


def test_w7_single_high_confidence_signal_never_auto_escalates():
    # 審査Q&A対策: シグナル1本(0.9)では high を即断しない。
    # points = 5 + 2 + 2 = 9 -> high, but n=1 caps confidence at 0.55 < 0.7
    out = main(synthetic_case([5], criticality="high", failed_tools=2))
    assert out.severity == "high"
    assert out.confidence == 0.55
    assert out.maestro_branch == "confidence_gap_review"
    assert out.recommended_action[0] == "analyst_review"


def test_w7_confidence_monotone_in_signal_count():
    # 同じ平均0.9でも、独立シグナルが増えるほど confidence 上限が上がる
    one = main(synthetic_case([1])).confidence          # cap 0.55
    two = main(synthetic_case([1, 1])).confidence       # cap 0.70
    four = main(synthetic_case([1, 1, 1, 1])).confidence  # cap 1.0 -> raw 0.9
    assert one == 0.55
    assert two == 0.7
    assert four == 0.9
    assert one < two < four


# --- W7: threshold boundaries (非circular: demo fixture と独立な合成ケース) ------

@pytest.mark.parametrize(
    "severities,expected",
    [
        ([4], "low"),            # 4 points: 強シグナル1本のみでは analyst queue に乗せない
        ([4, 1], "medium"),      # 5 points: 強シグナル + 何らかの裏付け
        ([4, 4], "medium"),      # 8 points
        ([4, 5], "high"),        # 9 points: 強シグナル2本相当
        ([4, 4, 5], "high"),     # 13 points
        ([5, 5, 4], "critical"), # 14 points: 独立した攻撃段階3つ相当
    ],
)
def test_w7_severity_threshold_boundaries(severities, expected):
    out = main(synthetic_case(severities))
    assert out.severity == expected
