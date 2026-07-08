"""judge routing"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from agentic.agent.cbt.distortions import DISTORTIONS
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.config.llm_models import CBT_JUDGE, build_llm
from agentic.gateway.monitoring import observe_langchain_usage


logger = logging.getLogger(__name__)


# langchain, fallback


try:  # pragma: no cover
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover

    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"



@dataclass(frozen=True)
class JudgeOutcome:
    """parsed, distortion, confidence"""

    technique: CBTTechnique
    reason: str
    distortion: str | None
    confidence: float
    rationale: str
    raw: str = ""

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.4


# buat format


_USER_TEMPLATE = (
    "Language: {language}\n\n"
    "User message:\n\"\"\"\n{message}\n\"\"\"\n\n"
    "Previous CBT directive (last turn):\n{last_directive}\n\n"
    "Active KG context (memory summary):\n{kg_context}\n\n"
    "Linguistic signals (register, slang hits, distress cues):\n"
    "{linguistic_signals}\n\n"
    "Recent conversation turns:\n{recent_turns}\n\n"
    "Opt-out cooldown info: declined_last={declined_last}, "
    "last_offered={last_offered}\n\n"
    "Respond with the JSON object only."
)


def _format_last_directive(cbt_state: dict[str, Any]) -> str:
    last = cbt_state.get("last_directive") or {}
    if not last:
        return "(none)"
    technique = last.get("technique") or "none"
    reason = last.get("reason") or ""
    payload = last.get("payload") or {}
    distortion = payload.get("distortion") or "none"
    return f"technique={technique}, reason={reason}, distortion={distortion}"


def _format_linguistic_signals(signals: dict[str, Any] | None) -> str:
    """render as str"""
    if not signals:
        return "(unavailable)"
    parts: list[str] = []
    register = signals.get("register")
    if register:
        parts.append(f"register={register}")
    slang_terms = signals.get("slang_terms") or []
    if slang_terms:
        parts.append(f"slang_hits={len(slang_terms)}")
    distress_terms = signals.get("distress_terms") or []
    if distress_terms:
        parts.append(f"distress_terms={','.join(distress_terms[:5])}")
    if signals.get("language_signal"):
        parts.append(f"lang_signal={signals['language_signal']}")
    return ", ".join(parts) if parts else "(no signal)"


def _format_recent_turns(
    history: list[dict[str, Any]] | None,
    *,
    k: int = 4,
) -> str:
    if not history:
        return "(none)"
    tail = history[-k:]
    lines: list[str] = []
    for entry in tail:
        role = (entry.get("role") or "?").strip()
        text = (entry.get("content") or entry.get("text") or "").strip()
        if not text:
            continue
        # trim lines, keep judge input short.
        snippet = text[:240]
        lines.append(f"[{role}] {snippet}")
    return "\n".join(lines) if lines else "(none)"



async def judge_technique(
    state: dict[str, Any],
    *,
    llm: Any | None = None,
) -> JudgeOutcome | None:
    """run judge call"""
    client = llm if llm is not None else _build_default_client()
    if client is None:
        return None

    cbt_state = state.get("cbt_state") or {}
    language = (
        state.get("resolved_language")
        or state.get("language_pref")
        or "id"
    )

    user_prompt = _USER_TEMPLATE.format(
        language=language,
        message=(state.get("current_message") or "").strip() or "(empty)",
        last_directive=_format_last_directive(cbt_state),
        kg_context=(state.get("kg_context") or "(none)").strip(),
        linguistic_signals=_format_linguistic_signals(
            state.get("linguistic_signals")
        ),
        recent_turns=_format_recent_turns(state.get("conversation_history")),
        declined_last=bool(cbt_state.get("declined_last_offer")),
        last_offered=cbt_state.get("last_offered") or "none",
    )

    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=CBT_JUDGE.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        observe_langchain_usage(ai, fallback_model=CBT_JUDGE.model)
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
    except Exception as exc:  # pragma: no cover defensive
        logger.warning("cbt judge call failed: %s", exc)
        return None

    return _parse_judge_output(raw)


def _build_default_client() -> Any | None:
    try:
        return build_llm(CBT_JUDGE)
    except Exception as exc:  # pragma: no cover defensive
        logger.warning("cbt judge build_llm failed: %s", exc)
        return None



_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


_VALID_TECHNIQUES: frozenset[str] = frozenset(t.value for t in CBTTechnique)


def _parse_judge_output(raw: str) -> JudgeOutcome | None:
    if not raw:
        logger.warning("cbt judge empty output")
        return None

    match = _JSON_RE.search(raw)
    payload = match.group(0) if match else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("cbt judge non-json: %r", raw[:200])
        return None

    technique_raw = str(data.get("technique") or "").strip().lower()
    if technique_raw in _VALID_TECHNIQUES:
        technique = CBTTechnique(technique_raw)
    else:
        logger.warning("cbt judge unknown technique: %r", technique_raw)
        technique = CBTTechnique.VALIDATE

    reason_raw = str(data.get("reason") or "judge_decision").strip()
    reason = reason_raw.replace(" ", "_").lower()[:64]

    distortion_raw = data.get("distortion")
    if isinstance(distortion_raw, str):
        key = distortion_raw.strip().lower()
        distortion = key if key in DISTORTIONS else None
    else:
        distortion = None

    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))

    rationale = str(data.get("rationale") or "").strip()[:200]

    return JudgeOutcome(
        technique=technique,
        reason=reason,
        distortion=distortion,
        confidence=confidence,
        rationale=rationale,
        raw=raw,
    )


__all__ = [
    "JudgeOutcome",
    "judge_technique",
]
