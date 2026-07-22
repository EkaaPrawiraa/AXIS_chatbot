"""get polini"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import yaml

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.prompts import load_prompt_bundle


logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class SensitivityTier:
    level: int
    label: str
    retrieval: str   # "full_text" | "summary_only" | "category_only"
    max_items: int
    importance_floor: float = 0.0


@dataclass(frozen=True)
class SensitivityPolicy:
    tiers: Mapping[int, SensitivityTier]
    suppress_flag_required: bool = True
    bitemporal_validity_required: bool = True
    user_override_honored: bool = True


_POLICY_CACHE: SensitivityPolicy | None = None


def load_policy(*, force_reload: bool = False) -> SensitivityPolicy:
    global _POLICY_CACHE
    if _POLICY_CACHE is not None and not force_reload:
        return _POLICY_CACHE

    bundle = load_prompt_bundle("guardrails/kg_sensitivity")
    parsed = yaml.safe_load(bundle.system) or {}
    if not isinstance(parsed, dict):
        raise ValueError("kg_sensitivity system block must parse to a mapping")

    tiers_raw = parsed.get("SENSITIVITY_TIERS") or {}
    tiers: dict[int, SensitivityTier] = {}
    for key, body in tiers_raw.items():
        try:
            level = int(key)
        except (TypeError, ValueError):
            continue
        tiers[level] = SensitivityTier(
            level=level,
            label=str(body.get("label", "")),
            retrieval=str(body.get("retrieval", "full_text")),
            max_items=int(body.get("max_items", 5)),
            importance_floor=float(body.get("importance_floor", 0.0)),
        )

    _POLICY_CACHE = SensitivityPolicy(
        tiers=tiers,
        suppress_flag_required=bool(parsed.get("SUPPRESS_FLAG_REQUIRED", True)),
        bitemporal_validity_required=bool(
            parsed.get("BITEMPORAL_VALIDITY_REQUIRED", True)
        ),
        user_override_honored=bool(parsed.get("USER_OVERRIDE_HONORED", True)),
    )
    return _POLICY_CACHE



@dataclass
class MemoryCandidate:
    """ambil data"""

    id: str
    sensitivity_level: int
    content: str
    summary: str | None = None
    category: str | None = None
    importance: float = 0.0
    suppressed: bool = False
    valid: bool = True
    source: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)



@dataclass(frozen=True)
class RenderedMemory:
    """append_to_prompt"""

    id: str
    text: str
    mode: str
    sensitivity_level: int


async def apply_sensitivity_policy(
    candidates: Iterable[MemoryCandidate],
    *,
    policy: SensitivityPolicy | None = None,
    audit: GuardrailLogger | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> tuple[RenderedMemory, ...]:
    """filter async, render sync"""
    policy = policy or load_policy()
    audit = audit or NullGuardrailLogger()

    rendered: list[RenderedMemory] = []
    counts_per_tier: dict[int, int] = {}

    for c in candidates:
        # open
        if policy.bitemporal_validity_required and not c.valid:
            await audit.log(
                GuardrailEvent(
                    user_id=user_id,
                    session_id=session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="invalid_skipped",
                    decision=GuardrailEventDecision.BLOCK,
                    severity=GuardrailEventSeverity.INFO,
                    trigger_detail=c.id,
                )
            )
            continue

        # sup
        if policy.suppress_flag_required and c.suppressed:
            await audit.log(
                GuardrailEvent(
                    user_id=user_id,
                    session_id=session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="user_suppressed_skipped",
                    decision=GuardrailEventDecision.BLOCK,
                    severity=GuardrailEventSeverity.INFO,
                    trigger_detail=c.id,
                )
            )
            continue

        tier = policy.tiers.get(c.sensitivity_level)
        if tier is None:
            # lvl3
            tier = policy.tiers.get(3)
            if tier is None:
                continue

        if c.importance < tier.importance_floor:
            continue

        already = counts_per_tier.get(tier.level, 0)
        if already >= tier.max_items:
            continue

        text = _render(c, tier)
        if text is None:
            continue

        rendered.append(
            RenderedMemory(
                id=c.id,
                text=text,
                mode=tier.retrieval,
                sensitivity_level=tier.level,
            )
        )
        counts_per_tier[tier.level] = already + 1

        if tier.retrieval != "full_text":
            await audit.log(
                GuardrailEvent(
                    user_id=user_id,
                    session_id=session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="redacted_memory",
                    decision=GuardrailEventDecision.REDACT,
                    severity=GuardrailEventSeverity.INFO,
                    trigger_detail=c.id,
                    metadata={
                        "level": tier.level,
                        "mode": tier.retrieval,
                    },
                )
            )

    return tuple(rendered)


def _render(c: MemoryCandidate, tier: SensitivityTier) -> str | None:
    if tier.retrieval == "full_text":
        return c.content or c.summary or ""
    if tier.retrieval == "summary_only":
        if c.summary:
            return c.summary
        if c.category:
            return f"Pola emosional terkait kategori: {c.category}"
        # pilih
        snippet = (c.content or "").split(".", 1)[0]
        return snippet.strip() or None
    if tier.retrieval == "category_only":
        if c.category:
            return f"Catatan sensitif tercatat (kategori: {c.category})."
        return "Catatan sensitif tercatat."
    return c.content or None


def serialize_block(rendered: Iterable[RenderedMemory]) -> str:
    """buat prompt"""
    by_mode: dict[str, list[str]] = {}
    for r in rendered:
        by_mode.setdefault(r.mode, []).append(r.text)

    parts: list[str] = []
    if by_mode.get("full_text"):
        parts.append("## Konteks dari percakapan sebelumnya:")
        for t in by_mode["full_text"]:
            parts.append(f"- {t}")
    if by_mode.get("summary_only"):
        parts.append("\n## Pola emosional yang tercatat (ringkasan saja):")
        for t in by_mode["summary_only"]:
            parts.append(f"- {t}")
    if by_mode.get("category_only"):
        parts.append("\n## Catatan sensitif (hanya kategori, jangan ungkap detail):")
        for t in by_mode["category_only"]:
            parts.append(f"- {t}")

    return "\n".join(parts).strip()


__all__ = [
    "SensitivityPolicy",
    "SensitivityTier",
    "MemoryCandidate",
    "RenderedMemory",
    "load_policy",
    "apply_sensitivity_policy",
    "serialize_block",
]
