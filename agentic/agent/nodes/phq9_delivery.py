"""skip"""

from __future__ import annotations

from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.phq9.subgraph import (
    WARMUP_TURNS_BEFORE_OFFER,
    phq9_subgraph_node,
)
from agentic.agent.state import ConversationState
from agentic.memory.assessment_repo import AssessmentRepository


__all__ = [
    "WARMUP_TURNS_BEFORE_OFFER",
    "phq9_delivery_node",
]


async def phq9_delivery_node(
    state: ConversationState,
    *,
    repo: AssessmentRepository,
    scorer_llm: Any | None = None,    # legacy alias; treated as judge_llm
    feedback_llm: Any | None = None,
    judge_llm: Any | None = None,
    clarification_llm: Any | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """delegasi ke subgraph phq-9. tetapkan untuk kompabilitas kelewatan, gunakan scorer_llm jika tidak diberikan."""
    audit = audit or NullGuardrailLogger()
    return await phq9_subgraph_node(
        state,
        repo=repo,
        judge_llm=judge_llm or scorer_llm,
        clarification_llm=clarification_llm,
        feedback_llm=feedback_llm,
        audit=audit,
    )
