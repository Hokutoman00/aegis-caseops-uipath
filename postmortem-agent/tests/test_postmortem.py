"""O4 postmortem: markdown contract + 不変量2（gaps 素通し）tests."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import PostmortemIn, main

# design.md M2 fixture (D2, exact values)
M2_FIXTURE = {
    "case_id": "INC-2026-0001",
    "severity": "critical",
    "confidence": 0.76,
    "case_stage": "human_approval",
    "recommended_action": ["network_isolation", "privilege_revocation"],
    "human_approval_required": True,
    "maestro_branch": "escalate_for_containment",
    "evidence": [
        "critical asset",
        "New admin role assigned",
        "Outbound transfer to unrecognized ASN",
        "splunk_search: Three correlated events found within 14 minutes.",
        "identity_graph: Role assignment originated from a non-standard admin workstation.",
    ],
    "gaps": ["asset_inventory: Inventory API timed out."],
    "rationale": "risk_points=15; confidence=0.76; signals=3; evidence_count=5; gap_count=1",
}


def render(**overrides) -> str:
    args = dict(
        case_id="INC-2026-0001",
        triage_json=json.dumps(M2_FIXTURE),
        approval_state="approved",
        ticket_id="MOCK-deadbeef",
        remediation_log=[
            "isolation executed (mock): network_isolation",
            "isolation executed (mock): privilege_revocation",
        ],
    )
    args.update(overrides)
    return main(PostmortemIn(**args)).postmortem_md


def test_d2_approved_includes_gaps_verbatim():
    md = render()
    # 不変量2: gap 文字列が無加工で postmortem に残る
    assert "- asset_inventory: Inventory API timed out." in md
    assert "MOCK-deadbeef" in md
    assert "isolation executed (mock): network_isolation" in md


def test_gaps_section_always_rendered_even_when_empty():
    fixture = {**M2_FIXTURE, "gaps": []}
    md = render(triage_json=json.dumps(fixture), approval_state="not_required")
    assert "## Gaps" in md
    assert "No gaps recorded" in md


def test_rejected_case_has_no_remediation_lines():
    # 不変量1の終端表現: 否認 case に remediation 実行行が出ない（否定的 assert, L1）
    md = render(approval_state="rejected")
    assert "not executed (human rejected)" in md
    assert "isolation executed" not in md
    assert "MOCK-" not in md


def test_low_risk_branch_not_applicable():
    fixture = {**M2_FIXTURE, "severity": "low", "maestro_branch": "low_risk_close", "gaps": []}
    md = render(triage_json=json.dumps(fixture), approval_state="not_required", remediation_log=[])
    assert "not applicable for this branch" in md


def test_malformed_triage_json_degrades_without_crash():
    # L3: JSON.parse 相当は型ガード。壊れた入力でも markdown は返り、gaps 節は残る
    md = render(triage_json="{not json", approval_state="not_required")
    assert "# Postmortem: INC-2026-0001" in md
    assert "## Gaps" in md
    assert "severity: unknown" in md
