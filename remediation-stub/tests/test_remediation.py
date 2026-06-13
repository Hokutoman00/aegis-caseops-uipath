"""O3 remediation stub: output contract + invariant tests (design.md O3 / 不変量1)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import RemediationIn, main

# D2 approved actions (M2 fixture: recommended_action after human approval)
D2_ACTIONS = ["network_isolation", "privilege_revocation"]


def test_output_contract_d2():
    out = main(RemediationIn(case_id="INC-2026-0001", approved_actions=D2_ACTIONS))
    assert re.fullmatch(r"MOCK-[0-9a-f]{8}", out.ticket_id)
    assert out.remediation_log == [
        "isolation executed (mock): network_isolation",
        "isolation executed (mock): privilege_revocation",
    ]


def test_log_is_one_line_per_action_in_order():
    actions = ["a", "b", "c"]
    out = main(RemediationIn(case_id="X", approved_actions=actions))
    assert len(out.remediation_log) == len(actions)
    assert [line.rsplit(": ", 1)[1] for line in out.remediation_log] == actions


def test_no_unapproved_action_leaks_into_log():
    # 不変量1の裏面: 承認されなかった action が log に現れない（否定的 assert, L1）
    out = main(RemediationIn(case_id="X", approved_actions=["network_isolation"]))
    assert all("privilege_revocation" not in line for line in out.remediation_log)


def test_empty_approval_produces_empty_log():
    out = main(RemediationIn(case_id="X", approved_actions=[]))
    assert out.remediation_log == []


def test_ticket_ids_are_unique_per_run():
    ids = {
        main(RemediationIn(case_id="X", approved_actions=[])).ticket_id
        for _ in range(20)
    }
    assert len(ids) == 20


def test_mock_marker_present_in_every_log_line():
    # デモ安全性: 実破壊と誤読されない marker が全行に入る
    out = main(RemediationIn(case_id="X", approved_actions=D2_ACTIONS))
    assert all("(mock)" in line for line in out.remediation_log)
