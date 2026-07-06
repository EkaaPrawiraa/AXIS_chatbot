"""CBT-aware dialogue policy node."""

from __future__ import annotations

import logging
import time
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.cbt import (
    CBTDecision,
    CBTTechnique,
    DEFAULT_DECISION,
    DISTORTIONS,
    ThoughtRecordMachine,
    route,
    route_with_llm,
)
from agentic.agent.cbt.thought_record import (
    ThoughtRecordStep,
    ThoughtRecordSubState,
)
from agentic.agent.state import ConversationState, empty_cbt_state


logger = logging.getLogger(__name__)



_DECLINE_CUES_ID: tuple[str, ...] = (
    "ga usah", "nanti aja", "skip", "lewatin", "ga mau", "engga",
    "nggak deh", "jangan dulu",
)
_DECLINE_CUES_EN: tuple[str, ...] = (
    "no thanks", "skip", "later", "not now", "rather not",
)


def _detected_decline(user_reply: str) -> bool:
    if not user_reply:
        return False
    lower = user_reply.lower()
    return any(c in lower for c in _DECLINE_CUES_ID) or any(
        c in lower for c in _DECLINE_CUES_EN
    )



async def dialogue_policy_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    machine: ThoughtRecordMachine | None = None,
    llm: Any | None = None,
    judge_llm: Any | None = None,
) -> ConversationState:
    """
    Choose the CBT technique for this turn and update sub-state.

    When ``judge_llm`` is provided the node uses the hybrid LLM-judge
    router; otherwise it falls back to the sync rule based router for
    backward compat.

    Parameters
    ----------
    state:
        Mutable conversation state.
    audit:
        Layer 0 audit logger.
    machine:
        Thought record sub-state machine. A default instance is used
        when omitted.
    llm:
        Optional LLM for the thought record reframe step.
    judge_llm:
        Optional pre-built LangChain client for the CBT judge. When
        absent, the node uses the sync rule based router.
    """
    audit = audit or NullGuardrailLogger()
    machine = machine or ThoughtRecordMachine()
    started = time.perf_counter()

    cbt_state = dict(state.get("cbt_state") or empty_cbt_state())

    # Detect a NEW decline of the previous offer. The cooldown flag
    # set by a prior turn is preserved here so the router can honor it
    # even when the new message is on a different topic. The cooldown
    # is consumed by the router (see post-routing block below) so it
    # only applies for one turn at a time.
    new_decline = False
    if cbt_state.get("last_offered") and _detected_decline(
        state.get("current_message") or ""
    ):
        new_decline = True
        cbt_state["declined_last_offer"] = True
        cbt_state["decline_streak"] = int(
            cbt_state.get("decline_streak", 0)
        ) + 1

    # Persist decline tracking before routing so the router sees it.
    state["cbt_state"] = cbt_state  # type: ignore[typeddict-item]

    if judge_llm is not None:
        decision = await route_with_llm(state, judge_llm=judge_llm)
    else:
        decision = route(state)

    # Consume the cooldown. The flag stays True for exactly one additional
    # turn after the decline so the router blocks the re-offer on the
    # NEXT turn as well. Only reset when the cooldown fires in a
    # subsequent turn (not the same turn where new_decline was detected).
    if decision.reason == "opt_out_cooldown":
        if not new_decline:
            cbt_state["declined_last_offer"] = False
        # else: decline just happened this turn — keep flag True so it
        # persists to the next turn and the cooldown applies there too.
    elif not new_decline:
        # Engaged turn that did not invoke cooldown: streak resets.
        cbt_state["decline_streak"] = 0

    # If a thought record is being driven, advance the machine.
    if decision.technique is CBTTechnique.THOUGHT_RECORD:
        decision = await _advance_thought_record(
            state=state,
            cbt_state=cbt_state,
            machine=machine,
            base_decision=decision,
            llm=llm,
        )

    # Mirror the decision into state for response generator + audit.
    cbt_state["last_directive"] = {
        "technique": decision.technique.value,
        "reason": decision.reason,
        "signals": list(decision.signals),
        "payload": dict(decision.payload),
    }
    if not decision.is_none and decision.technique is not CBTTechnique.VALIDATE:
        cbt_state["last_offered"] = decision.technique.value
    elif decision.is_none:
        # safety/phq9 path: keep prior last_offered
        pass

    state["cbt_state"] = cbt_state  # type: ignore[typeddict-item]
    state["cbt_node_active"] = decision.technique.value
    state["cbt_directive"] = cbt_state["last_directive"]  # type: ignore[typeddict-item]

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await _audit_decision(audit, state, decision, elapsed_ms)
    return state



async def _advance_thought_record(
    *,
    state: ConversationState,
    cbt_state: dict[str, Any],
    machine: ThoughtRecordMachine,
    base_decision: CBTDecision,
    llm: Any | None,
) -> CBTDecision:
    """Drive the thought record sub-state machine by one step."""
    sub_state_dict = cbt_state.get("thought_record")
    sub_state = ThoughtRecordSubState.from_dict(sub_state_dict)

    user_reply = (
        state.get("current_message") or ""
        if cbt_state.get("thought_record_active")
        else ""
    )

    hinted_name = base_decision.payload.get("distortion") if isinstance(
        base_decision.payload.get("distortion"), str
    ) else None
    hinted_distortion = (
        DISTORTIONS.get(hinted_name) if hinted_name else None
    )
    language = state.get("resolved_language") or "id"

    turn = await machine.step(
        sub_state=sub_state,
        user_reply=user_reply,
        language=language,
        hinted_distortion=hinted_distortion,
        llm=llm,
    )

    cbt_state["thought_record"] = turn.next_state.to_dict()
    cbt_state["thought_record_active"] = not turn.completed

    payload = dict(base_decision.payload)
    payload["step"] = turn.next_state.step.value
    payload["bot_prompt"] = turn.bot_prompt
    payload["completed"] = turn.completed

    return CBTDecision(
        technique=base_decision.technique,
        reason=base_decision.reason,
        signals=base_decision.signals + (
            "thought_record_step",
        ),
        payload=payload,
    )



async def _audit_decision(
    audit: GuardrailLogger,
    state: ConversationState,
    decision: CBTDecision,
    latency_ms: int,
) -> None:
    severity = (
        GuardrailEventSeverity.INFO
        if decision.technique
        in (CBTTechnique.NONE, CBTTechnique.VALIDATE)
        else GuardrailEventSeverity.WARN
    )
    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,  # closest existing layer label
            event_type=f"cbt_{decision.technique.value}",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=severity,
            trigger_detail=decision.reason,
            latency_ms=latency_ms,
            metadata={
                "signals": list(decision.signals),
                "payload": dict(decision.payload),
            },
        )
    )


__all__ = ["dialogue_policy_node"]
