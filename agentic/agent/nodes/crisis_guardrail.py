"""Layer 3 pre-generation safety + tiered crisis response pipeline."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.state import ConversationState
from agentic.gateway.monitoring import increment, observe_langchain_usage
from agentic.prompts import load_prompt_bundle


logger = logging.getLogger(__name__)


# Pre-generation crisis check


@dataclass(frozen=True)
class PreGenRules:
    crisis_phrases: tuple[str, ...]
    threshold: float
    embedding_model: str | None


_PREGEN_CACHE: PreGenRules | None = None


def load_pregen_rules(*, force_reload: bool = False) -> PreGenRules:
    global _PREGEN_CACHE
    if _PREGEN_CACHE is not None and not force_reload:
        return _PREGEN_CACHE

    bundle = load_prompt_bundle("guardrails/pre_generation")
    parsed = yaml.safe_load(bundle.system) or {}
    if not isinstance(parsed, dict):
        raise ValueError("pre_generation system block must parse to a mapping")

    phrases = tuple(parsed.get("CRISIS_SIGNAL_PHRASES") or [])
    threshold = float(parsed.get("CRISIS_SEMANTIC_THRESHOLD", 0.82))
    model = parsed.get("EMBEDDING_MODEL")

    _PREGEN_CACHE = PreGenRules(
        crisis_phrases=tuple(p.lower() for p in phrases),
        threshold=threshold,
        embedding_model=str(model) if model else None,
    )
    return _PREGEN_CACHE


_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ']+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _dice(a: Iterable[str], b: Iterable[str]) -> float:
    """Dice coefficient — less penalising for length asymmetry than Jaccard.

    Dice = 2|A∩B| / (|A|+|B|). A short crisis phrase fully embedded in a
    longer utterance scores ~2n/(n+m) rather than Jaccard's n/(n+m+diff),
    which keeps short exact matches above the detection threshold even when
    the user message spans several sentences.
    """
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return 2 * len(sa & sb) / (len(sa) + len(sb))


@dataclass(frozen=True)
class PreGenDecision:
    crisis: bool
    similarity: float
    matched_phrase: str | None


def evaluate_pregen(
    message: str, rules: PreGenRules | None = None
) -> PreGenDecision:
    """
    Pre-generation crisis detector. Tokenizes the message and each crisis
    phrase, computes Dice coefficient overlap, and flags when the best match
    exceeds the configured threshold.
    """
    rules = rules or load_pregen_rules()
    if not message.strip():
        return PreGenDecision(crisis=False, similarity=0.0, matched_phrase=None)

    msg_tokens = _tokenize(message)
    best_score = 0.0
    best_phrase: str | None = None
    for phrase in rules.crisis_phrases:
        s = _dice(msg_tokens, _tokenize(phrase))
        if s > best_score:
            best_score = s
            best_phrase = phrase

    return PreGenDecision(
        crisis=best_score >= rules.threshold,
        similarity=best_score,
        matched_phrase=best_phrase,
    )


# PHQ-9 routing helper


_PHQ9_ACTIVE_PHASES = frozenset(
    {"offered", "in_progress", "awaiting_clar"}
)


def _phq9_is_active(state: ConversationState) -> bool:
    """True when PHQ-9 is mid-administration. Crisis is deferred.

    `offer_pending` is intentionally excluded: at that phase the scheduler
    has only marked PHQ-9 as ready to offer; the user has not been engaged
    yet (offer_made_at_turn is None). Deferring crisis here would mask
    explicit tier-1 intent during free chat.
    """
    phq9 = state.get("phq9_state") or {}
    phase = phq9.get("phase", "idle")
    return phase in _PHQ9_ACTIVE_PHASES



@dataclass(frozen=True)
class _Tier1Keywords:
    """Compiled tier 1 keyword patterns (active/explicit intent only)."""

    patterns_id: tuple[re.Pattern[str], ...]
    patterns_en: tuple[re.Pattern[str], ...]

    def matches(self, text: str) -> bool:
        """Return True when ``text`` contains any tier 1 keyword."""
        lowered = text.lower()
        return any(
            pat.search(lowered) is not None
            for pat in (*self.patterns_id, *self.patterns_en)
        )


_TIER1_CACHE: _Tier1Keywords | None = None
_LETTER = r"[A-Za-zÀ-ɏḀ-ỿ]"
_BOUND_PRE = rf"(?<!{_LETTER})"
_BOUND_POST = rf"(?!{_LETTER})"


def _compile_kw(kw: str) -> re.Pattern[str]:
    return re.compile(
        _BOUND_PRE + re.escape(kw.lower()) + _BOUND_POST,
        re.IGNORECASE,
    )


def _load_tier1_keywords(*, force_reload: bool = False) -> _Tier1Keywords:
    """
    Load TIER1_CRISIS_KEYWORDS_ID/EN from guardrails/input_validation.yaml.

    Tier 1 keywords are a strict subset of CRISIS_KEYWORDS and represent
    explicit active intent (e.g. "mau bunuh diri", "kill myself"). They
    are compiled with the same Unicode-aware word-boundary anchors used
    by ``input_guardrail_node``.
    """
    global _TIER1_CACHE
    if _TIER1_CACHE is not None and not force_reload:
        return _TIER1_CACHE

    bundle = load_prompt_bundle("guardrails/input_validation")
    parsed = yaml.safe_load(bundle.system) or {}

    kws_id = list(parsed.get("TIER1_CRISIS_KEYWORDS_ID") or [])
    kws_en = list(parsed.get("TIER1_CRISIS_KEYWORDS_EN") or [])

    if not kws_id:
        logger.warning(
            "crisis_guardrail: TIER1_CRISIS_KEYWORDS_ID is empty; "
            "all Indonesian crisis signals will be treated as tier 2."
        )

    _TIER1_CACHE = _Tier1Keywords(
        patterns_id=tuple(_compile_kw(k) for k in kws_id),
        patterns_en=tuple(_compile_kw(k) for k in kws_en),
    )
    return _TIER1_CACHE


def _classify_crisis_tier(
    state: ConversationState,
    tier1_kws: _Tier1Keywords,
) -> str:
    """
    Return "1" (explicit active intent) or "2" (passive ideation).

    Decision table:
    - PHQ-9 item9 route_to_crisis_after -> "2": the questionnaire
      records ideation frequency, not a live statement of intent.
    - Layer 2 keyword match -> check matched text against tier1 patterns:
      "1" if it matches, "2" if it does not.
    - Layer 3 semantic (Jaccard) detection -> "2": the heuristic is
      less precise than an exact keyword; default to conservative tier.
    """
    phq9 = state.get("phq9_state") or {}
    if phq9.get("route_to_crisis_after"):
        return "2"

    input_decision = state.get("input_guardrail") or {}
    reason = input_decision.get("reason", "")
    matched = str(input_decision.get("matched") or "")

    if reason in ("crisis_keyword_id", "crisis_keyword_en") and matched:
        return "1" if tier1_kws.matches(matched) else "2"

    # Semantic or unknown origin -> conservative.
    return "2"


def _clear_handled_phq9_crisis_route(state: ConversationState) -> None:
    """Mark a deferred PHQ-9 safety follow-up as handled for later turns."""
    phq9 = dict(state.get("phq9_state") or {})
    if not phq9.get("route_to_crisis_after"):
        return
    phq9["route_to_crisis_after"] = False
    if phq9.get("phase") == "deferred_crisis":
        phq9["phase"] = "completed"
    state["phq9_state"] = phq9  # type: ignore[typeddict-item]


# Pre-generation node


async def crisis_guardrail_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    rules: PreGenRules | None = None,
) -> ConversationState:
    """
    Pre-generation crisis check. Sets ``state["safety_flag"] = "crisis"``
    when triggered, but defers when PHQ-9 is mid-administration so the
    questionnaire can finish first; ``phq9_delivery_node`` will set
    ``route_to_crisis_after`` based on item 9 score.
    """
    audit = audit or NullGuardrailLogger()
    started = time.perf_counter()

    # If Layer 2 already escalated, mirror the flag (subject to PHQ-9).
    input_decision = (state.get("input_guardrail") or {}).get("decision")
    if input_decision == "escalate_crisis":
        if not _phq9_is_active(state):
            state["safety_flag"] = "crisis"
            increment("crisis_guardrail_events_total", tier="input", route="triage")
        return state

    message = state.get("current_message") or ""
    verdict = evaluate_pregen(message, rules=rules)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if verdict.crisis:
        if _phq9_is_active(state):
            # Mark deferral in state so downstream audit queries and the
            # session finalizer can see a signal was present but skipped.
            # _turn_init_node clears this at the start of the next turn.
            state["deferred_crisis_signal"] = True
            increment("crisis_guardrail_events_total", tier="semantic", route="deferred_phq9")
            await audit.log(
                GuardrailEvent(
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    layer=GuardrailEventLayer.PRE_GEN,
                    event_type="semantic_crisis_deferred_phq9",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=verdict.matched_phrase,
                    latency_ms=elapsed_ms,
                    metadata={"similarity": verdict.similarity},
                )
            )
            return state

        state["safety_flag"] = "crisis"
        increment("crisis_guardrail_events_total", tier="semantic", route="triage")
        await audit.log(
            GuardrailEvent(
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
                layer=GuardrailEventLayer.PRE_GEN,
                event_type="semantic_crisis",
                decision=GuardrailEventDecision.ESCALATE,
                severity=GuardrailEventSeverity.CRITICAL,
                trigger_detail=verdict.matched_phrase,
                latency_ms=elapsed_ms,
                metadata={"similarity": verdict.similarity},
            )
        )

    return state


# Crisis triage (convergence point)


async def crisis_triage_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    tier1_kws: _Tier1Keywords | None = None,
) -> ConversationState:
    """
    Convergence node for all crisis signals.

    Reads the trigger origin and matched keyword from state, classifies
    the signal as Tier 1 (explicit active intent) or Tier 2 (passive
    ideation / distress), and writes ``state["crisis_tier"]``.

    The graph's conditional edge after this node routes to
    ``crisis_escalation_node`` for tier 1 and ``crisis_empathy_node``
    for tier 2.

    This node does NOT produce a response itself -- it is purely a
    classifier and router.
    """
    audit = audit or NullGuardrailLogger()
    kws = tier1_kws or _load_tier1_keywords()
    tier = _classify_crisis_tier(state, kws)

    state["crisis_tier"] = tier
    increment("crisis_guardrail_events_total", tier=tier, route="triage")

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.PRE_GEN,
            event_type="crisis_triage",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=f"tier={tier}",
            metadata={"crisis_tier": tier},
        )
    )
    return state


def route_after_crisis_triage(state: ConversationState) -> str:
    """
    Conditional edge: tier 1 -> crisis_escalation, tier 2 -> crisis_empathy.

    Called by the LangGraph conditional routing after ``crisis_triage_node``.
    """
    return (
        "crisis_escalation"
        if state.get("crisis_tier") == "1"
        else "crisis_empathy"
    )


# Crisis empathy (tier 2 LLM response + deterministic resources)


def _render_hotline_context(resources: CrisisResources | None = None) -> str:
    """Render a compact `name — contact` listing for LLM grounding.

    Returned as plain text suitable for inlining into a system prompt so the
    LLM has the canonical hotline names + numbers in context. Not part of the
    user-facing response — the deterministic resource block handles that.
    """
    try:
        cat = resources or load_crisis_resources()
    except Exception:
        return ""
    lines: list[str] = []
    for resource in cat.items.values():
        contact = resource.contact_text if hasattr(resource, "contact_text") else _format_contact(resource.contact)
        if not contact:
            continue
        lines.append(f"- {resource.name} — {contact}")
    return "\n".join(lines)


def render_resource_block(
    resources: CrisisResources | None = None,
    state: ConversationState | None = None,
) -> str:
    """
    Build the deterministic resource block appended after the tier 2
    LLM empathy response.

    The block is intentionally short: a one-line lead-in followed by
    the selected resource list. Format mirrors the tier 1 template so
    the user sees a consistent pattern regardless of tier.
    """
    lines = (resources or load_crisis_resources()).selected_lines(state)
    return f"Kontak bantuan dari sistem yang bisa kamu hubungi:\n\n{lines}"


async def crisis_empathy_node(
    state: ConversationState,
    *,
    llm: Any,
    audit: GuardrailLogger | None = None,
    resources: CrisisResources | None = None,
) -> ConversationState:
    """
    Tier 2 crisis response: LLM-generated empathy + deterministic resources.

    The LLM is called with the ``CRISIS_EMPATHY`` system prompt (AFSP
    Safe Messaging Guidelines). It produces 3-4 sentences that acknowledge
    the user's specific pain without advice, clinical labels, or resource
    numbers. The deterministic resource block is appended after -- the
    LLM never produces hotline numbers (eliminates hallucination risk and
    guarantees resource accuracy).

    On LLM failure the node falls back to the tier 1 deterministic
    template so the user always receives a safe response.

    Parameters
    ----------
    llm:
        A LangChain chat model built from ``CRISIS_EMPATHY`` spec.
        Passed from the graph builder via ``functools.partial`` or a
        closure -- the node signature follows the LangGraph pattern of
        injecting dependencies through partial application.
    """
    audit = audit or NullGuardrailLogger()
    started = time.perf_counter()

    message = state.get("current_message") or ""
    phq9 = state.get("phq9_state") or {}
    previous_final = (state.get("final_response") or "").strip()
    if phq9.get("route_to_crisis_after") and previous_final:
        message = (
            f"{message}\n\n"
            "Context: PHQ-9 has already been completed and scored. "
            "Do not ask the user to remember item answers or continue the "
            "questionnaire. Give only a brief safety follow-up."
        )

    from agentic.config.llm_models import CRISIS_EMPATHY

    # Pass the canonical hotline list as system context so the LLM can ground
    # any reference to "ada layanan yang bisa membantu" against real names,
    # rather than confabulating brands or numbers. The LLM is still instructed
    # by the prompt itself to omit numbers inline (the resource block prints
    # them deterministically afterward).
    resource_ctx = _render_hotline_context(resources)
    system_prompt = CRISIS_EMPATHY.system_prompt
    if resource_ctx:
        system_prompt = f"{system_prompt}\n\n=== REFERENSI LAYANAN (untuk konteks, JANGAN diulang inline) ===\n{resource_ctx}"

    try:
        lc_response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message),
            ]
        )
        empathy_text = (lc_response.content or "").strip()
        observe_langchain_usage(lc_response, fallback_model=getattr(llm, "model_name", None))
        if not empathy_text:
            raise ValueError("LLM returned empty empathy response")
    except Exception as exc:
        logger.error(
            "crisis_empathy_node: LLM call failed, falling back to tier 1 template: %s",
            exc,
        )
        increment("crisis_guardrail_events_total", tier="2", route="empathy_fallback")
        # Fall back to the deterministic tier 1 template so the user
        # always receives a structurally safe response.
        state["final_response"] = render_crisis_response(resources, state=state)
        _clear_handled_phq9_crisis_route(state)
        state["crisis_escalated"] = True  # type: ignore[typeddict-unknown-key]
        state["safety_flag"] = "crisis"
        return state

    resource_block = render_resource_block(resources, state)
    state["final_response"] = f"{empathy_text}\n\n{resource_block}"
    _clear_handled_phq9_crisis_route(state)
    state["crisis_escalated"] = True  # type: ignore[typeddict-unknown-key]
    state["safety_flag"] = "crisis"

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.PRE_GEN,
            event_type="crisis_empathy_generated",
            decision=GuardrailEventDecision.ESCALATE,
            severity=GuardrailEventSeverity.CRITICAL,
            trigger_detail="tier2_llm_response",
            latency_ms=elapsed_ms,
        )
    )
    return state


# Crisis escalation (tier 1, deterministic)


@dataclass(frozen=True)
class CrisisResource:
    key: str
    name: str
    contact: Any
    availability: str
    contact_methods: tuple[str, ...] = ()
    audience: Any = None
    support_type: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    url: str = ""

    @property
    def contact_text(self) -> str:
        return _format_contact(self.contact)

    def as_line(self) -> str:
        contact = self.contact_text
        parts = [self.name]
        if contact:
            parts.append(contact)
        line = ": ".join(parts)
        if self.contact_methods:
            line = f"{line} [{', '.join(self.contact_methods)}]"
        if self.availability:
            line = f"{line} ({self.availability})"
        return f"- {line}"


@dataclass(frozen=True)
class CrisisResources:
    items: Mapping[str, CrisisResource]

    def get(self, key: str) -> CrisisResource | None:
        return self.items.get(key)

    def _field(self, key: str, field: str, default: str) -> str:
        resource = self.get(key)
        if resource is None:
            return default
        return str(getattr(resource, field, default) or default)

    @property
    def primary_name(self) -> str:
        return self._field("primary", "name", "Layanan Krisis")

    @property
    def primary_contact(self) -> str:
        resource = self.get("primary")
        return resource.contact_text if resource else ""

    @property
    def primary_availability(self) -> str:
        return self._field("primary", "availability", "")

    @property
    def campus_name(self) -> str:
        return self._field("campus", "name", "Layanan Kampus")

    @property
    def campus_contact(self) -> str:
        resource = self.get("campus")
        return resource.contact_text if resource else ""

    def selected_lines(
        self,
        state: ConversationState | None = None,
        *,
        max_lines: int = 8,
    ) -> str:
        keys = _select_resource_keys(state)
        resources = [
            self.items[key]
            for key in keys
            if key in self.items
        ]
        return "\n".join(r.as_line() for r in resources[:max_lines])

    def as_template_args(
        self,
        state: ConversationState | None = None,
    ) -> dict[str, str]:
        return {
            "resource_lines": self.selected_lines(state),
            # Backward-compatible placeholders for older templates.
            "primary_name": self.primary_name,
            "primary_contact": self.primary_contact,
            "primary_availability": self.primary_availability,
            "campus_name": self.campus_name,
            "campus_contact": self.campus_contact,
        }


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(v) for v in value if v is not None)
    return (str(value),)


def _humanize_contact_key(key: str) -> str:
    labels = {
        "id": "ID",
        "en": "EN",
        "email": "Email",
        "phone": "Telepon",
        "fax_or_phone": "Fax/telepon",
        "whatsapp_admin": "WhatsApp admin",
    }
    return labels.get(key, key.replace("_", " ").title())


def _format_contact(contact: Any) -> str:
    if contact is None:
        return ""
    if isinstance(contact, Mapping):
        parts = []
        for key, value in contact.items():
            if value in (None, ""):
                continue
            parts.append(f"{_humanize_contact_key(str(key))}: {value}")
        return "; ".join(parts)
    if isinstance(contact, Sequence) and not isinstance(contact, (str, bytes)):
        return "; ".join(str(v) for v in contact if v not in (None, ""))
    return str(contact)


def _state_text_for_resource_selection(
    state: ConversationState | None,
) -> str:
    if not state:
        return ""
    chunks = [
        state.get("current_message") or "",
        state.get("kg_context") or "",
    ]
    for message in state.get("messages") or []:
        if isinstance(message, dict):
            chunks.append(str(message.get("content") or ""))
    return " ".join(chunks).lower()


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _select_resource_keys(
    state: ConversationState | None = None,
) -> tuple[str, ...]:
    """
    Choose a short deterministic set of resources.

    Emergency and the primary hotline are always shown. Additional
    resources are selected from the same YAML based on explicit context
    so the crisis response stays actionable rather than becoming a full
    directory dump.
    """
    text = _state_text_for_resource_selection(state)
    keys = ["emergency", "primary", "secondary"]

    if _contains_any(
        text,
        (
            "abuse",
            "abused",
            "domestic violence",
            "sexual",
            "rape",
            "kdrt",
            "kekerasan",
            "pelecehan",
            "dipukul",
            "pemerkosaan",
            "perkosaan",
            "disakiti pasangan",
        ),
    ):
        keys.extend(("women_and_children", "women_crisis_center"))

    if _contains_any(
        text,
        (
            "itb",
            "kampus",
            "campus",
            "kuliah",
            "mahasiswa",
            "student",
            "dosen",
            "tugas akhir",
            "skripsi",
            "thesis",
        ),
    ):
        keys.append("campus")

    if _contains_any(
        text,
        (
            "konseling",
            "counseling",
            "counselling",
            "psikolog",
            "psychologist",
            "terapi",
            "therapy",
            "trauma",
        ),
    ):
        keys.append("additional_counseling")

    if _contains_any(
        text,
        (
            "alternatif",
            "alternative",
            "opsi lain",
            "other option",
            "layanan lain",
            "resource lain",
        ),
    ):
        keys.append("reference")

    return tuple(dict.fromkeys(keys))


_RESOURCES_CACHE: CrisisResources | None = None
_DEFAULT_RESOURCES_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "crisis_resources.yaml"
)


def load_crisis_resources(
    path: Path | None = None,
    *,
    force_reload: bool = False,
) -> CrisisResources:
    global _RESOURCES_CACHE
    if _RESOURCES_CACHE is not None and not force_reload:
        return _RESOURCES_CACHE

    target = path or _DEFAULT_RESOURCES_PATH
    if not target.is_file():
        raise FileNotFoundError(f"crisis resources file not found: {target}")
    with target.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    items: dict[str, CrisisResource] = {}
    for key, raw in data.items():
        if not isinstance(raw, dict):
            continue
        items[str(key)] = CrisisResource(
            key=str(key),
            name=str(raw.get("name", key)),
            contact=raw.get("contact", ""),
            availability=str(raw.get("availability", "")),
            contact_methods=_string_tuple(raw.get("contact_methods")),
            audience=raw.get("audience"),
            support_type=_string_tuple(raw.get("support_type")),
            scope=_string_tuple(raw.get("scope")),
            url=str(raw.get("url", "")),
        )

    _RESOURCES_CACHE = CrisisResources(items=items)
    return _RESOURCES_CACHE


def render_crisis_response(
    resources: CrisisResources | None = None,
    state: ConversationState | None = None,
) -> str:
    """Render the deterministic crisis response without an LLM."""
    bundle = load_prompt_bundle("guardrails/crisis_response")
    template = bundle.system
    args = (resources or load_crisis_resources()).as_template_args(state)
    try:
        return template.format(**args)
    except KeyError as exc:
        logger.warning("crisis template missing placeholder %s", exc)
        return template


async def crisis_escalation_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    resources: CrisisResources | None = None,
) -> ConversationState:
    """
    Tier 1 crisis response. Always deterministic -- no LLM involved.

    Called only when ``crisis_triage_node`` classifies the signal as
    tier 1 (explicit active intent: "mau bunuh diri", "kill myself",
    etc.). Returns the warm deterministic template from
    ``guardrails/crisis_response.yaml`` with the resource block rendered
    from ``config/crisis_resources.yaml``.

    The audit event layer reflects the actual triggering origin:
    - ``INPUT``   when Layer 2 keyword check triggered escalation.
    - ``PRE_GEN`` when Layer 3 Jaccard check triggered escalation.
    - ``PRE_GEN`` when PHQ-9 item 9 triggered deferred escalation.
    """
    audit = audit or NullGuardrailLogger()
    phq9 = state.get("phq9_state") or {}
    input_decision = state.get("input_guardrail") or {}

    if phq9.get("route_to_crisis_after"):
        reason = "phq9_item9"
        trigger_layer = GuardrailEventLayer.PRE_GEN
    elif input_decision.get("reason"):
        # Escalation was initiated by Layer 2 (keyword match).
        reason = input_decision["reason"]
        trigger_layer = GuardrailEventLayer.INPUT
    else:
        reason = "semantic_pre_gen"
        trigger_layer = GuardrailEventLayer.PRE_GEN

    state["final_response"] = render_crisis_response(resources, state=state)
    _clear_handled_phq9_crisis_route(state)
    state["crisis_escalated"] = True  # type: ignore[typeddict-unknown-key]
    state["safety_flag"] = "crisis"
    increment("crisis_guardrail_events_total", tier="1", route="escalation")

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=trigger_layer,
            event_type="crisis_escalation",
            decision=GuardrailEventDecision.ESCALATE,
            severity=GuardrailEventSeverity.CRITICAL,
            trigger_detail=str(reason),
        )
    )
    return state


__all__ = [
    # Pre-generation check
    "PreGenRules",
    "PreGenDecision",
    "load_pregen_rules",
    "evaluate_pregen",
    "crisis_guardrail_node",
    # Triage
    "_Tier1Keywords",
    "_load_tier1_keywords",
    "crisis_triage_node",
    "route_after_crisis_triage",
    # Tier 1 escalation
    "CrisisResource",
    "CrisisResources",
    "load_crisis_resources",
    "render_crisis_response",
    "crisis_escalation_node",
    # Tier 2 empathy
    "render_resource_block",
    "crisis_empathy_node",
]
