"""Verdict integrity re-audit (invariant 3, layer-3 blind grader).

Recomputes the deterministic triage from the raw incident JSON and diffs the
verdict fields against the triage JSON attached to the case. If anything —
an LLM agent, a workflow edit, a manual patch — altered the verdict after M1
wrote it, this exits non-zero and prints the diff.

Usage:
    python verify_verdict.py <incident.json> <triage.json>
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import IncidentCaseIn, main

VERDICT_FIELDS = [
    "severity",
    "maestro_branch",
    "human_approval_required",
    "recommended_action",
    "confidence",
]


def verify(incident: dict, triage: dict) -> list[str]:
    """Return a list of human-readable mismatches (empty = verdict intact)."""
    if not isinstance(incident, dict) or not isinstance(triage, dict):
        return ["input is not a JSON object"]
    recomputed = asdict(main(IncidentCaseIn(**incident)))
    mismatches = []
    for field in VERDICT_FIELDS:
        if recomputed[field] != triage.get(field):
            mismatches.append(
                f"{field}: recomputed={recomputed[field]!r} attached={triage.get(field)!r}"
            )
    return mismatches


def cli(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    incident = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    triage = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    mismatches = verify(incident, triage)
    if mismatches:
        print(f"VERDICT TAMPERED ({len(mismatches)} field(s)):")
        for m in mismatches:
            print(f"  - {m}")
        return 1
    print("verdict intact: all verdict fields match the deterministic core")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv))
