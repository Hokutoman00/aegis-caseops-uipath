"""Invariant 3 layer-3 (blind grader): verdict re-audit detects tampering."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import IncidentCaseIn, main
from verify_verdict import verify

DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"

ALL_FIXTURES = [
    "incident-case-001.json",
    "incident-case-002-low.json",
    "incident-case-003-gap.json",
]


def load(name: str) -> dict:
    return json.loads((DEMO_DATA / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_untouched_verdict_passes(name):
    incident = load(name)
    triage = asdict(main(IncidentCaseIn(**incident)))
    assert verify(incident, triage) == []


def test_llm_style_severity_downgrade_is_detected():
    # 想定攻撃: LLM/後段が critical を medium に「説明し直す」
    incident = load("incident-case-001.json")
    triage = asdict(main(IncidentCaseIn(**incident)))
    triage["severity"] = "medium"
    triage["maestro_branch"] = "request_more_evidence"
    mismatches = verify(incident, triage)
    assert any(m.startswith("severity:") for m in mismatches)
    assert any(m.startswith("maestro_branch:") for m in mismatches)


def test_approval_bypass_is_detected():
    # 想定攻撃: human_approval_required を false に書き換えて承認ゲートを迂回
    incident = load("incident-case-001.json")
    triage = asdict(main(IncidentCaseIn(**incident)))
    triage["human_approval_required"] = False
    mismatches = verify(incident, triage)
    assert mismatches == [
        "human_approval_required: recomputed=True attached=False"
    ]


def test_non_verdict_fields_are_not_audited():
    # explanation 等の非判定フィールドは M4 (LLM) の領分 — 監査対象外
    incident = load("incident-case-002-low.json")
    triage = asdict(main(IncidentCaseIn(**incident)))
    triage["explanation_md"] = "LLM-generated narrative (allowed to vary)"
    assert verify(incident, triage) == []
