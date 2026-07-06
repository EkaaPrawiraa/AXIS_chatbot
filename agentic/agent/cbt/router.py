"""CBT technique router."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from agentic.agent.cbt.distortions import (
    Distortion,
    DISTORTIONS,
    detect_distortion_in_text,
)
from agentic.agent.cbt.judge import JudgeOutcome, judge_technique
from agentic.agent.cbt.techniques import (
    CBTDecision,
    CBTTechnique,
    DEFAULT_DECISION,
)


logger = logging.getLogger(__name__)



SELF_CRITICISM_CUES_ID: tuple[str, ...] = (
    "aku payah", "aku gagal", "aku bodoh", "aku bener-bener buruk",
    "aku ga berguna", "aku selalu salah", "aku bego", "aku goblok",
)
SELF_CRITICISM_CUES_EN: tuple[str, ...] = (
    "i am stupid", "i am a failure", "i hate myself", "i am worthless",
    "i am the worst",
)


AVOIDANCE_CUES_ID: tuple[str, ...] = (
    "ga sanggup ngapa-ngapain", "diam aja seharian", "tidur seharian",
    "ga keluar kamar", "skip kelas", "ga balas chat", "menghilang",
)
AVOIDANCE_CUES_EN: tuple[str, ...] = (
    "stayed in bed", "skipped class", "ignored everyone", "couldnt do anything",
)


# Emotion-disclosure cues: used only to gate the terminal fallback
# between VALIDATE (the user shared a feeling, even mild) and NONE
# (ordinary conversation, nothing emotional to respond to). None of
# the more specific branches above (distortion, avoidance, self
# criticism, psychoed) need this list -- they already imply emotional
# content on their own. Deliberately broad and low-bar: false positives
# here just mean an ordinary-conversation turn gets validate instead of
# none, which was the old universal behavior anyway and is always safe.
EMOTION_CUES_ID: tuple[str, ...] = (
    "sedih", "capek", "cape", "lelah", "kesel", "kesal", "marah", "takut",
    "cemas", "khawatir", "nangis", "galau", "stress", "stres", "tertekan",
    "kecewa", "down", "badmood", "bete", "males", "malas", "bosen", "bosan",
    "putus asa", "hampa", "kosong", "sendirian", "kesepian", "gagal",
    "susah", "berat banget", "overwhelmed", "burnout", "insecure",
    "minder", "gak pede", "ga pede", "sakit hati", "kepikiran",
    "gelisah", "resah", "capek banget", "capek hidup",
)
EMOTION_CUES_EN: tuple[str, ...] = (
    "sad", "tired", "exhausted", "angry", "scared", "anxious", "worried",
    "crying", "stressed", "depressed", "disappointed", "overwhelmed",
    "burnout", "lonely", "hopeless", "empty", "insecure", "down",
)


PSYCHOED_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"apa (sih |itu )?(yang dimaksud|maksudnya)\b", re.IGNORECASE),
    re.compile(r"\b(jelasin|definisi|apa beda)\b", re.IGNORECASE),
    re.compile(r"\bwhat (does|is|are) (this|that|cbt|ema|distortion)\b", re.IGNORECASE),
    # Questions about "why do I feel like this / is this normal / am I crazy?"
    re.compile(r"\b(gak|ga|tidak)\s+paham\s+(kenapa|mengapa)\b", re.IGNORECASE),
    # Require self-referential anchor to avoid matching "kenapa kamu tiba-tiba pergi"
    re.compile(r"\bkenapa\b.{0,20}\b(aku|gue|gw|saya)\b.{0,20}\btiba-tiba\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bkenapa\b.{0,10}\btiba-tiba\b.{0,20}\b(nangis|ngerasa|sedih|takut|panik|menangis)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bapa\s+(aku|ini|itu)\s+(gila|normal|wajar)\b", re.IGNORECASE),
    re.compile(r"\bnangis\s+tanpa\s+(alasan|sebab)\b", re.IGNORECASE),
    re.compile(r"\b(why\s+(do|am)\s+i|is\s+this\s+normal|am\s+i\s+(crazy|okay))\b", re.IGNORECASE),
)


REFRAME_REQUEST_CUES_ID: tuple[str, ...] = (
    "bantu reframe", "gimana cara mikirnya", "cara nge-rephrase",
    "bantu lihat dari sisi lain",
)
REFRAME_REQUEST_CUES_EN: tuple[str, ...] = (
    "help me reframe", "another perspective", "challenge this thought",
)


# Crisis / PHQ-9 phases that block CBT entirely.
SAFETY_TECHNIQUE_BLOCKLIST: frozenset[str] = frozenset(
    {"crisis", "escalate"}
)
_PHQ9_ACTIVE_PHASES: frozenset[str] = frozenset(
    {"offer_pending", "offered", "in_progress", "awaiting_clar"}
)



@dataclass(frozen=True)
class CBTSignals:
    """Reduced state surface the router actually needs."""

    user_message: str
    language: str
    distortion: Distortion | None
    distortion_from_context: bool
    self_criticism: bool
    avoidance: bool
    psychoeducation_request: bool
    reframe_request: bool
    in_progress_thought_record: bool
    last_offered: str | None
    declined_last: bool
    has_emotional_content: bool


_TOPIC_SHIFT_CUES: tuple[str, ...] = (
    "ngomong-ngomong",
    "omong-omong",
    "btw",
    "by the way",
    "anyway",
    "oh iya",
    "sidenote",
)

_CONTINUATION_CUES_ID: tuple[str, ...] = (
    "iya",
    "ya",
    "yup",
    "bener",
    "betul",
    "setuju",
    "hmm",
    "hmmm",
    "gimana ya",
    "terus",
    "lanjut",
    "oke",
    "ok",
)


def _distortion_from_name(name: str | None) -> Distortion | None:
    if not name:
        return None
    key = name.strip().lower()
    return DISTORTIONS.get(key)


def _is_topic_shift(lower_msg: str) -> bool:
    return any(cue in lower_msg for cue in _TOPIC_SHIFT_CUES)


def _is_continuation_message(msg: str, lower_msg: str) -> bool:
    # Only treat as continuation when there is an explicit cue.
    if not msg:
        return False
    stripped = msg.strip()
    if stripped in ("?", "??", "???"):
        return True
    if len(stripped) <= 48 and any(cue in lower_msg for cue in _CONTINUATION_CUES_ID):
        return True
    return False


def _extract_active_distortion_names_from_kg_context(kg_context: str) -> list[str]:
    if not kg_context:
        return []
    lowered = kg_context.lower()
    header = "[unchallenged cognitive distortions]"
    start = lowered.find(header)
    if start == -1:
        return []
    # Slice to next section header (line starting with '[').
    after = kg_context[start + len(header) :]
    end_idx = after.find("\n[")
    section = after if end_idx == -1 else after[:end_idx]

    names: list[str] = []
    for line in section.splitlines():
        m = re.search(r"\[([a-z_]+)\]", line)
        if not m:
            continue
        name = m.group(1).strip().lower()
        if name in DISTORTIONS:
            names.append(name)
    return names


def _infer_context_distortion(state: dict[str, Any]) -> Distortion | None:
    cbt_state = state.get("cbt_state") or {}
    last_directive = cbt_state.get("last_directive") or {}
    payload = last_directive.get("payload") or {}
    hinted = _distortion_from_name(payload.get("distortion"))
    if hinted is not None:
        return hinted

    # Last resort: use the most recent unchallenged distortion from KG context.
    kg_context = state.get("kg_context") or ""
    for name in _extract_active_distortion_names_from_kg_context(kg_context):
        d = _distortion_from_name(name)
        if d is not None:
            return d
    return None


def _has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(c in text for c in cues)


def extract_signals(state: dict[str, Any]) -> CBTSignals:
    """Reduce the conversation state to the inputs the router uses."""
    msg = (state.get("current_message") or "").strip()
    lower = msg.lower()
    language = state.get("resolved_language") or state.get("language_pref") or "id"

    cbt_state = state.get("cbt_state") or {}
    in_progress_tr = bool(cbt_state.get("thought_record_active"))
    last_offered = cbt_state.get("last_offered")
    declined_last = bool(cbt_state.get("declined_last_offer"))

    self_crit = _has_any(lower, SELF_CRITICISM_CUES_ID) or _has_any(
        lower, SELF_CRITICISM_CUES_EN
    )
    avoidance = _has_any(lower, AVOIDANCE_CUES_ID) or _has_any(
        lower, AVOIDANCE_CUES_EN
    )
    psychoed = any(p.search(msg) for p in PSYCHOED_CUES)
    reframe_req = _has_any(lower, REFRAME_REQUEST_CUES_ID) or _has_any(
        lower, REFRAME_REQUEST_CUES_EN
    )

    distortion = detect_distortion_in_text(msg)
    distortion_from_context = False

    # Gate for the terminal fallback (validate vs none). Corpus-driven
    # distress_terms (linguistic_enrichment_node, high emotional weight
    # phrases) count too, on top of the broader everyday emotion-word
    # list above -- either is enough to treat the turn as emotional.
    linguistic_signals = state.get("linguistic_signals") or {}
    has_distress_term = bool(linguistic_signals.get("distress_terms"))
    has_emotional_content = (
        has_distress_term
        or _has_any(lower, EMOTION_CUES_ID)
        or _has_any(lower, EMOTION_CUES_EN)
    )

    # Continuation heuristic: if the user is clearly continuing the
    # prior CBT thread (short acknowledgement / follow-up) and the
    # previous directive contained a distortion, we allow that prior
    # distortion to anchor the next turn.
    if (
        distortion is None
        and not _is_topic_shift(lower)
        and _is_continuation_message(msg, lower)
    ):
        last_directive = (cbt_state.get("last_directive") or {})
        last_technique = str(last_directive.get("technique") or "")
        if last_technique in (CBTTechnique.REFRAME.value, CBTTechnique.THOUGHT_RECORD.value):
            inferred = _infer_context_distortion(state)
            if inferred is not None:
                distortion = inferred
                distortion_from_context = True

    return CBTSignals(
        user_message=msg,
        language=language if language in ("id", "en") else "id",
        distortion=distortion,
        distortion_from_context=distortion_from_context,
        self_criticism=self_crit,
        avoidance=avoidance,
        psychoeducation_request=psychoed,
        reframe_request=reframe_req,
        in_progress_thought_record=in_progress_tr,
        last_offered=last_offered,
        declined_last=declined_last,
        has_emotional_content=has_emotional_content,
    )



def _rule_safety_check(state: dict[str, Any]) -> CBTDecision | None:
    """
    Hard safety rules that always win over any soft routing.

    Returns a :class:`CBTDecision` when a safety rule fires, ``None``
    otherwise so the caller can proceed to soft routing (rule based
    tree or LLM judge).
    """
    safety_flag = state.get("safety_flag")
    if safety_flag in SAFETY_TECHNIQUE_BLOCKLIST:
        return CBTDecision(
            technique=CBTTechnique.NONE,
            reason="safety_flag_blocked",
            signals=("safety_flag",),
        )

    phq9_phase = (state.get("phq9_state") or {}).get("phase", "idle")
    if phq9_phase in _PHQ9_ACTIVE_PHASES:
        return CBTDecision(
            technique=CBTTechnique.NONE,
            reason="phq9_active",
            signals=("phq9_active",),
        )

    s = extract_signals(state)

    # Resume in-progress thought record.
    if s.in_progress_thought_record:
        return CBTDecision(
            technique=CBTTechnique.THOUGHT_RECORD,
            reason="thought_record_in_progress",
            signals=("thought_record_active",),
        )

    return None


def route(state: dict[str, Any]) -> CBTDecision:
    """Pick the technique that fits this turn using sync rule tree."""
    blocked = _rule_safety_check(state)
    if blocked is not None:
        return blocked

    s = extract_signals(state)

    cbt_state = state.get("cbt_state") or {}
    last_offered = cbt_state.get("last_offered")
    last_directive_payload = (
        (cbt_state.get("last_directive") or {}).get("payload") or {}
    )

    # Explicit reframe request escalates straight to thought record if
    # we already have a distortion to anchor on.
    if s.reframe_request and s.distortion is not None:
        return _maybe_offer(
            CBTTechnique.THOUGHT_RECORD,
            "reframe_request_with_distortion",
            ("reframe_request", "distortion"),
            s,
            payload={"distortion": s.distortion.name},
        )

    # Active distortion: escalate to thought_record when the same
    # distortion was reframed last turn (CBT progression: Socratic → record).
    if s.distortion is not None:
        prior_distortion = last_directive_payload.get("distortion")
        if (
            last_offered == CBTTechnique.REFRAME.value
            and prior_distortion == s.distortion.name
        ):
            return _maybe_offer(
                CBTTechnique.THOUGHT_RECORD,
                "reframe_escalation",
                ("reframe_escalation", "distortion"),
                s,
                payload={"distortion": s.distortion.name},
            )
        return _maybe_offer(
            CBTTechnique.REFRAME,
            "context_distortion" if s.distortion_from_context else "active_distortion",
            ("distortion_context",) if s.distortion_from_context else ("distortion",),
            s,
            payload={"distortion": s.distortion.name},
        )

    # Avoidance cue: behavior activation (Beck & Beck 2011).
    if s.avoidance:
        return _maybe_offer(
            CBTTechnique.BEHAVIOR_ACTIVATION,
            "avoidance_cue",
            ("avoidance",),
            s,
        )

    if s.self_criticism:
        # After self_compassion was already offered, escalate to thought
        # record so the user can examine the self-critical belief in depth.
        if last_offered == CBTTechnique.SELF_COMPASSION.value:
            return _maybe_offer(
                CBTTechnique.THOUGHT_RECORD,
                "self_compassion_escalation",
                ("self_criticism", "self_compassion_escalation"),
                s,
            )
        return _maybe_offer(
            CBTTechnique.SELF_COMPASSION,
            "self_criticism_cue",
            ("self_criticism",),
            s,
        )

    if s.psychoeducation_request:
        return CBTDecision(
            technique=CBTTechnique.PSYCHOEDUCATION,
            reason="user_definition_question",
            signals=("psychoed_cue",),
        )

    # Terminal fallback: nothing more specific fired. The companion
    # role isn't limited to CBT/validation -- ordinary conversation
    # with no emotional content should just be ordinary conversation
    # (no overlay), not validated by default. Only fall through to
    # validate when the turn actually discloses a feeling.
    if not s.has_emotional_content:
        return CBTDecision(
            technique=CBTTechnique.NONE,
            reason="casual_no_emotional_content",
            signals=("no_emotional_content",),
        )

    return CBTDecision(
        technique=CBTTechnique.VALIDATE,
        reason="default_validate",
    )


def _maybe_offer(
    technique: CBTTechnique,
    reason: str,
    signals: tuple[str, ...],
    s: CBTSignals,
    *,
    payload: dict[str, object] | None = None,
) -> CBTDecision:
    """
    Honor user opt-out: if the user declined the same technique on the
    previous turn, fall back to validate for one turn before
    re-offering.
    """
    if s.declined_last and s.last_offered == technique.value:
        return CBTDecision(
            technique=CBTTechnique.VALIDATE,
            reason="opt_out_cooldown",
            signals=("opt_out_cooldown",) + signals,
            payload={"deferred": technique.value},
        )
    return CBTDecision(
        technique=technique,
        reason=reason,
        signals=signals,
        payload=payload or {},
    )


# Hybrid async route: rule safety -> LLM judge -> sync fallback


# Confidence below this threshold causes the judge result to be
# treated as advisory and we defer to the sync rule based router.
JUDGE_CONFIDENCE_THRESHOLD: float = 0.4


def _apply_opt_out_cooldown(
    technique: CBTTechnique,
    signals: CBTSignals,
) -> CBTTechnique:
    """
    Demote to VALIDATE if the user just declined the same technique.

    Mirrors :func:`_maybe_offer` for the LLM-judge path so cooldown
    semantics stay consistent across both routers.
    """
    if signals.declined_last and signals.last_offered == technique.value:
        return CBTTechnique.VALIDATE
    return technique


def _judge_outcome_to_decision(
    outcome: JudgeOutcome,
    signals: CBTSignals,
) -> CBTDecision:
    """Translate a :class:`JudgeOutcome` into a :class:`CBTDecision`."""
    technique = outcome.technique
    cooled_technique = _apply_opt_out_cooldown(technique, signals)

    payload: dict[str, object] = {}
    extra_signals: tuple[str, ...] = ("llm_judge",)
    if outcome.confidence:
        payload["confidence"] = outcome.confidence
    if outcome.rationale:
        payload["rationale"] = outcome.rationale

    # Surface distortion from the judge or from KG context so the
    # response_generator overlay can anchor the Socratic question.
    distortion_name: str | None = outcome.distortion
    if distortion_name is None and signals.distortion is not None:
        distortion_name = signals.distortion.name
        extra_signals = extra_signals + ("kg_distortion",)
    if distortion_name is not None:
        payload["distortion"] = distortion_name

    if cooled_technique is not technique:
        # User just declined this; demote with telemetry.
        return CBTDecision(
            technique=CBTTechnique.VALIDATE,
            reason="opt_out_cooldown",
            signals=("opt_out_cooldown", "llm_judge"),
            payload={"deferred": technique.value, **payload},
        )

    return CBTDecision(
        technique=cooled_technique,
        reason=outcome.reason or "llm_judge",
        signals=extra_signals,
        payload=payload,
    )


async def route_with_llm(
    state: dict[str, Any],
    *,
    judge_llm: Any | None,
    confidence_threshold: float = JUDGE_CONFIDENCE_THRESHOLD,
) -> CBTDecision:
    """
    Hybrid router: safety rules first, then LLM judge, then sync fallback.

    Parameters
    ----------
    state:
        ConversationState style dict.
    judge_llm:
        Optional pre-built LangChain client passed to the judge. If
        ``None``, the judge constructs its own client from
        :data:`agentic.config.llm_models.CBT_JUDGE`.
    confidence_threshold:
        Judge results with confidence below this value are treated as
        advisory; the router defers to :func:`route`.

    Returns
    -------
    A :class:`CBTDecision`. Never returns ``None``; the fallback to
    :func:`route` guarantees a value.
    """
    blocked = _rule_safety_check(state)
    if blocked is not None:
        return blocked

    try:
        outcome = await judge_technique(state, llm=judge_llm)
    except Exception as exc:  # pragma: no cover defensive
        logger.warning("cbt judge raised, falling back to rules: %s", exc)
        outcome = None

    if outcome is None:
        logger.info("cbt judge unavailable, using rule based route")
        return route(state)

    if outcome.confidence < confidence_threshold:
        logger.info(
            "cbt judge low confidence (%.2f < %.2f), falling back to rules",
            outcome.confidence,
            confidence_threshold,
        )
        return route(state)

    signals = extract_signals(state)
    return _judge_outcome_to_decision(outcome, signals)


__all__ = [
    "JUDGE_CONFIDENCE_THRESHOLD",
    "SAFETY_TECHNIQUE_BLOCKLIST",
    "CBTSignals",
    "extract_signals",
    "route",
    "route_with_llm",
]
