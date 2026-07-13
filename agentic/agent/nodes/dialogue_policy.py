"""set pol"""

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



DECLINE_STREAK_SUPPRESS_THRESHOLD: int = 2


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
    """update_substate()"""
    audit = audit or NullGuardrailLogger()
    machine = machine or ThoughtRecordMachine()
    started = time.perf_counter()

    cbt_state = dict(state.get("cbt_state") or empty_cbt_state())

    # detect, cooldown, route, flag.
    new_decline = False
    if cbt_state.get("last_offered") and _detected_decline(
        state.get("current_message") or ""
    ):
        new_decline = True
        cbt_state["declined_last_offer"] = True
        cbt_state["decline_streak"] = int(
            cbt_state.get("decline_streak", 0)
        ) + 1

    # buat nyimpan decline tracking
    state["cbt_state"] = cbt_state  # type: ignore[typeddict-item]

    if judge_llm is not None:
        decision = await route_with_llm(state, judge_llm=judge_llm)
    else:
        decision = route(state)

    # stop cycling, fall back to plain validation, cooldown.
    if (
        int(cbt_state.get("decline_streak", 0)) >= DECLINE_STREAK_SUPPRESS_THRESHOLD
        and decision.technique not in (CBTTechnique.NONE, CBTTechnique.VALIDATE)
    ):
        decision = CBTDecision(
            technique=CBTTechnique.VALIDATE,
            reason="decline_streak_suppressed",
            signals=("decline_streak",),
            payload={"suppressed_technique": decision.technique.value},
        )

    # reset on next turn
    if decision.reason == "opt_out_cooldown":
        if not new_decline:
            cbt_state["declined_last_offer"] = False
        # keep flag True, keep looping, cooldown.
    elif decision.reason == "decline_streak_suppressed":
        # leave streak, suppress keep holding.
        pass
    elif not new_decline and decision.technique in (
        CBTTechnique.NONE,
        CBTTechnique.VALIDATE,
    ):
        # clears streak, reset on diff tech.
        cbt_state["decline_streak"] = 0

    # driving, a.
    if decision.technique is CBTTechnique.THOUGHT_RECORD:
        decision = await _advance_thought_record(
            state=state,
            cbt_state=cbt_state,
            machine=machine,
            base_decision=decision,
            llm=llm,
        )

    # init state
    cbt_state["last_directive"] = {
        "technique": decision.technique.value,
        "reason": decision.reason,
        "signals": list(decision.signals),
        "payload": dict(decision.payload),
    }
    if not decision.is_none and decision.technique is not CBTTechnique.VALIDATE:
        cbt_state["last_offered"] = decision.technique.value
    elif decision.is_none:
        # keep last_offered
        pass

    # Track how long the conversation has stayed in pure validate/none mode
    # without a real technique, so the judge (route_with_llm) can lean
    # toward a more Socratic/directive pick instead of validating forever
    # (mirrors a therapist becoming more assertive when passive listening
    # alone is not surfacing the automatic thought).
    if decision.technique in (CBTTechnique.NONE, CBTTechnique.VALIDATE):
        cbt_state["turns_since_technique"] = int(
            cbt_state.get("turns_since_technique", 0)
        ) + 1
    else:
        cbt_state["turns_since_technique"] = 0

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
    """driving 1st."""
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
