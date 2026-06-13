"""Aegis CaseOps remediation stub — UiPath coded agent entrypoint.

design.md O3: runs only after the human approval gate (O2' queue approval in
the BPMN mainline; O2 Action Center if re-enabled). Demo-safe by design — no
real destructive action is taken: ticket creation is mocked and isolation is
recorded as a log line only. The output `remediation_log` is bound to a case
variable and feeds O4 postmortem directly (no external API, no reliance on
Orchestrator logs).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class RemediationIn:
    case_id: str
    approved_actions: list[str] = field(default_factory=list)


@dataclass
class RemediationOut:
    ticket_id: str
    remediation_log: list[str]


def main(input: RemediationIn) -> RemediationOut:
    ticket_id = "MOCK-" + uuid.uuid4().hex[:8]
    remediation_log = [
        f"isolation executed (mock): {action}" for action in input.approved_actions
    ]
    return RemediationOut(ticket_id=ticket_id, remediation_log=remediation_log)
