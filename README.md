# Aegis CaseOps — Governed Security Incident Remediation on UiPath Maestro

Noisy security alerts become governed, human-approved remediation — with a verdict no LLM can touch and anyone can re-audit.

**UiPath AgentHack 2026 submission** · Track: Maestro BPMN

## Why

Security automation fails in two ways: too slow, or too trigger-happy. CaseOps is built around four declared invariants that make the pipeline trustworthy enough to act:

1. **No remediation without human approval** — the approval-required edge is structurally the only BPMN path into remediation.
2. **Gaps propagate untouched** — every failed enrichment tool is recorded and shown verbatim at intake, approval, and postmortem.
3. **Only the deterministic core writes the verdict** — the LLM assistant is read-only, enforced at three layers (prompt/tool restriction, BPMN variable binding, blind-grader re-audit).
4. **One input schema** — all scenarios share the same alert contract.

## Operating impact (illustrative model)

*Illustrative model with stated assumptions — not measured production data.*

For a mid-size SOC at ~1,000 alerts/week, with ~60% low-severity auto-closable noise and ~15 min of manual triage per alert:

- **~150 analyst-hours/week** redirected from copy-paste triage to real investigation (~600 low-severity alerts/week handled deterministically).
- **The expensive failure mode is engineered out, not policed:** a single flaky high-confidence signal cannot auto-isolate a production server — the corroboration cap (one signal ≤ 0.55) structurally cannot auto-escalate, and remediation is reachable *only* through the human approval gate.
- **Escalations arrive decision-ready:** recommended actions *and* the explicit gaps are pre-rendered, so the analyst approves with full epistemic context instead of rebuilding it.

The adoption thesis: a CISO can deploy this because the verdict is deterministic, re-auditable, and the LLM is provably locked out of the decision — the three things that normally block automation from touching incident response.

## Architecture

```
alert JSON ──▶ API workflow ──▶ Maestro BPMN process
                                   │
                          [task_triage]  caseops-agent (deterministic, no LLM)
                                   │
                              XOR gateway
        ┌──────────────┬───────────────┬──────────────────┐
   low_risk_close  request_more_  confidence_gap_   escalate_for_
        │           evidence        review           containment
        │                                                │
        │                                    queue: caseops-approval
        │                                      (human approves with
        │                                       evidence AND gaps)
        │                                                │
        │                                      remediation-stub (mock)
        └──────────────────┬─────────────────────────────┘
                    postmortem-agent ──▶ markdown (gaps included)

   side channel: M4 analyst assistant (Agent Builder + Context Grounding)
                 — explains cases with citations; cannot write the verdict
```

## Components

| Path | What it is |
|---|---|
| `caseops-agent/` | Deterministic triage core (UiPath coded agent, plain `uipath` SDK). Risk points + corroboration-capped confidence: `min(avg, 0.40 + 0.15 × signals)` — a single signal can never exceed 0.55, so one signal never auto-escalates. |
| `caseops-agent/verify_verdict.py` | **Blind grader.** Recomputes the verdict from the raw alert and diffs the five verdict fields. Tampered verdict → non-zero exit. |
| `caseops-agent/evaluations/` | A custom `uipath eval` evaluator that scores all three demo verdicts; a deliberately tampered expected-set drops one case below 1.0, proving the evaluator is not a rubber stamp. |
| `maestro/caseops-process.bpmn` | Maestro process: one XOR gateway, four condition edges, approval gate. Imports into Studio Web's Agentic Process designer with 0 validation issues. |
| `remediation-stub/` | Mock remediation (ticket + log). No destructive actions in demo. |
| `postmortem-agent/` | Deterministic postmortem renderer. Gaps section always rendered; survives malformed input. |
| `demo-data/` | Three scenarios: D1 low-risk auto-close, D2 critical escalation with gap-visible approval, D3 degraded-tooling confidence-gap review. |

## Try the re-audit yourself

```bash
python -m venv .venv && .venv/Scripts/pip install uipath pytest

# run the full suite (per-dir)
.venv/Scripts/python -m pytest caseops-agent/tests remediation-stub/tests postmortem-agent/tests

# recompute & verify a verdict from the raw alert
.venv/Scripts/python caseops-agent/verify_verdict.py demo-data/incident-case-001.json triage-001.json
# → "verdict intact" (exit 0). Now edit any verdict field in triage-001.json:
# → "VERDICT TAMPERED (1 field(s))" (exit 1)
```

A 38-case pytest suite pins the demo scenarios, all four invariants (with negative asserts), severity threshold boundaries (4/5, 8/9, 13/14 on synthetic cases), and tamper detection.

## Severity model (and why the thresholds aren't arbitrary)

Each signal carries severity 0–5. `medium ≥ 5` = one strong signal (4) plus any corroboration; `high ≥ 9` = two strong signals; `critical ≥ 14` = three independent attack stages. Verified by boundary tests independent of the demo fixtures. Confidence below 0.7 on high/critical always reroutes to analyst review.

## Built with a coding agent

Designed and implemented end-to-end with Claude Code: design doc → adversarial design review (blind grader) → TDD. The commit history is the audit trail.

## License

MIT — see [LICENSE](LICENSE).
