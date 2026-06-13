"""Deterministic verdict evaluator for the caseops triage agent.

Scores an agent execution by comparing the four verdict fields against the
expected values declared in the eval set. Mirrors the verdict-field contract
audited by verify_verdict.py (invariant 3, blind grader).
"""

from uipath.eval.evaluators import (
    BaseEvaluationCriteria,
    BaseEvaluator,
    BaseEvaluatorConfig,
)
from uipath.eval.models import (
    AgentExecution,
    ErrorEvaluationResult,
    EvaluationResult,
    NumericEvaluationResult,
)


class CaseopsVerdictEvaluationCriteria(BaseEvaluationCriteria):
    """Expected verdict fields (subset of verify_verdict.VERDICT_FIELDS)."""

    expected_severity: str
    expected_branch: str
    expected_approval: bool
    expected_confidence: float


class CaseopsVerdictEvaluatorConfig(BaseEvaluatorConfig[CaseopsVerdictEvaluationCriteria]):
    """Configuration for the caseops-verdict evaluator."""

    name: str = "CaseopsVerdictEvaluator"


class CaseopsVerdictEvaluator(
    BaseEvaluator[CaseopsVerdictEvaluationCriteria, CaseopsVerdictEvaluatorConfig, str]
):
    """Score = fraction of verdict fields that match the expected values."""

    @classmethod
    def get_evaluator_id(cls) -> str:
        return "CaseopsVerdictEvaluator"

    async def evaluate(
        self,
        agent_execution: AgentExecution,
        evaluation_criteria: CaseopsVerdictEvaluationCriteria,
    ) -> EvaluationResult:
        output = agent_execution.agent_output
        if not isinstance(output, dict):
            return ErrorEvaluationResult(
                details=f"agent output is not a dict: {type(output).__name__}"
            )

        checks = {
            "severity": (output.get("severity"), evaluation_criteria.expected_severity),
            "maestro_branch": (output.get("maestro_branch"), evaluation_criteria.expected_branch),
            "human_approval_required": (
                output.get("human_approval_required"),
                evaluation_criteria.expected_approval,
            ),
            "confidence": (output.get("confidence"), evaluation_criteria.expected_confidence),
        }
        mismatches = [
            f"{field}: actual={actual!r} expected={expected!r}"
            for field, (actual, expected) in checks.items()
            if actual != expected
        ]
        return NumericEvaluationResult(
            score=(len(checks) - len(mismatches)) / len(checks),
            details="; ".join(mismatches) if mismatches else "all verdict fields match",
        )
