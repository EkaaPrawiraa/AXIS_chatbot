"""Response generation node."""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, replace
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.state import ConversationState
from agentic.config.llm_models import (
    RESPONSE_GENERATOR,
    build_llm,
    llm_provider,
    resolve_llm_model,
)
from agentic.gateway.monitoring import observe_langchain_usage
from agentic.memory.assessment_repo import AssessmentRepository
from agentic.prompts import load_prompt


logger = logging.getLogger(__name__)


_NON_HUMAN_DISPLAY_NAME_PARTS = {
    "scenario",
    "seed",
    "test",
    "testing",
    "codex",
    "local",
    "example",
    "admin",
}


def _looks_like_human_display_name(value: str) -> bool:
    name = value.strip()
    if not (2 <= len(name) <= 40):
        return False
    lowered = name.lower()
    if "@" in lowered or any(part in lowered for part in _NON_HUMAN_DISPLAY_NAME_PARTS):
        return False
    if re.fullmatch(r"[0-9a-f]{8,}(-[0-9a-f]{4,}){2,}", lowered):
        return False
    if re.search(r"[_+]", name):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", name))


def _polish_companion_style(text: str) -> str:
    """Small deterministic cleanup for phrases models overuse despite prompt rules."""
    cleaned = (text or "").strip()
    cleaned = re.sub(
        r"^\s*wah,\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


try:  # pragma: no cover
    from langchain_core.messages import (  # type: ignore[import-not-found]
        AIMessage as _AIMessage,
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
        ToolMessage as _ToolMessage,
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

    @dataclass
    class _AIMessage:  # type: ignore[no-redef]
        content: str
        type: str = "ai"

    @dataclass
    class _ToolMessage:  # type: ignore[no-redef]
        content: str
        tool_call_id: str = ""
        type: str = "tool"


_IDENTITY_PROMPT_REF = "system/axis_identity"
_BASE_PROMPT_REF = "nodes/response_generator"
_BASE_PROMPT_REF_V2 = "nodes/response_generator_v2"



def _base_prompt() -> str:
    try:
        return load_prompt(_BASE_PROMPT_REF_V2)
    except Exception as exc:
        logger.warning("base prompt load failed: %s", exc)
        return ""


def _identity_prompt() -> str:
    try:
        return load_prompt(_IDENTITY_PROMPT_REF)
    except Exception as exc:
        logger.warning("identity prompt load failed: %s", exc)
        return ""


def _technique_overlay(state: ConversationState) -> tuple[str, str | None]:
    technique = state.get("cbt_node_active")
    directive = state.get("cbt_directive") or {}
    payload = directive.get("payload") or {}

    if technique is None or technique == CBTTechnique.NONE.value:
        return "", None

    bot_prompt: str | None = None
    if technique == CBTTechnique.THOUGHT_RECORD.value:
        bot_prompt = payload.get("bot_prompt") if isinstance(payload, dict) else None

    prompt_ref_map = {
        CBTTechnique.VALIDATE.value: "cbt/validate",
        CBTTechnique.REFRAME.value: "cbt/reframe",
        CBTTechnique.THOUGHT_RECORD.value: "cbt/thought_record",
        CBTTechnique.BEHAVIOR_ACTIVATION.value: "cbt/behavior_activation",
        CBTTechnique.GROUNDING.value: "cbt/grounding",
        CBTTechnique.PSYCHOEDUCATION.value: "cbt/psychoeducation",
        CBTTechnique.SELF_COMPASSION.value: "cbt/self_compassion",
    }
    ref = prompt_ref_map.get(technique)
    if ref is None:
        return "", bot_prompt
    try:
        return load_prompt(ref), bot_prompt
    except Exception as exc:
        logger.warning("technique overlay load failed (%s): %s", ref, exc)
        return "", bot_prompt


def _format_history(state: ConversationState, *, last_n_pairs: int = 4) -> list[Any]:
    history = state.get("messages") or []
    take = last_n_pairs * 2
    out: list[Any] = []
    for msg in history[-take:]:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            out.append(_HumanMessage(content=content))
        elif role == "assistant":
            out.append(_AIMessage(content=content))
    return out


def _profile_context_block(state: ConversationState) -> str:
    profile = state.get("profile_context") or {}
    if not isinstance(profile, dict):
        return ""

    display_name = str(profile.get("display_name") or "").strip()
    preferred_language = str(profile.get("preferred_language") or "").strip()
    gender = str(profile.get("gender") or "").strip().lower()
    if gender not in ("pria", "wanita"):
        gender = ""
    mood_present = bool(profile.get("mood_today_score") or profile.get("mood_trend"))
    if not display_name and not preferred_language and not gender and not mood_present:
        return ""

    safe_name = display_name.replace("\n", " ").replace("\r", " ").strip()
    if safe_name and not _looks_like_human_display_name(safe_name):
        safe_name = ""
    parts = [
        "USER PROFILE CONTEXT:",
        "- Use this only for natural personalization; do not mention database, profile lookup, or internal state.",
    ]
    if safe_name:
        parts.append(f"- display_name: {safe_name}")
        parts.append("- You may greet or refer to the user by this name when it feels natural, but DO NOT overuse it.")
    if preferred_language:
        parts.append(f"- preferred_language: {preferred_language}")
    if gender:
        parts.append(f"- sex gender: {gender}")

    mood_today = str(profile.get("mood_today_score") or "").strip()
    mood_trend = str(profile.get("mood_trend") or "").strip()
    if mood_today:
        parts.append(
            f"- mood_check_in_today (1=sangat sedih .. 5=senang): {mood_today}"
        )
    if mood_trend and "," in mood_trend:
        parts.append(f"- mood_trend_last_7_days (oldest to newest, 1-5 scale): {mood_trend}")
    if mood_today or mood_trend:
        parts.append(
            "- You may acknowledge the user's current/recent mood naturally if relevant to "
            "the conversation, but do not explicitly cite these numbers or mention that mood "
            "was 'recorded' or 'logged' — treat it as something you simply sense about them."
        )

    return "\n".join(parts)


_SECTION_SEP = "\n\n" + "=" * 50 + "\n\n"


def _build_messages(state: ConversationState) -> list[Any]:
    parts: list[str] = []

    base = _base_prompt()
    if base:
        parts.append(base)

    identity = _identity_prompt()
    if identity:
        parts.append(identity)

    overlay, bot_prompt = _technique_overlay(state)
    if overlay:
        parts.append(overlay)

    if bot_prompt:
        parts.append(
            "Deterministic content for this turn (must be echoed in the "
            "reply, after one short acknowledgement):\n\n" + bot_prompt
        )

    # Memory context comes before offer overlay so PHQ directive is last / freshest.
    kg_context = (state.get("kg_context") or "").strip()
    if kg_context and not bot_prompt:
        parts.append(kg_context)

    url_context = (state.get("url_context") or "").strip()
    if url_context:
        parts.append(url_context)

    profile_context = _profile_context_block(state)
    if profile_context:
        parts.append(profile_context)

    phq9_state = state.get("phq9_state") or {}
    if (
        phq9_state.get("phase") == "offer_pending"
        and phq9_state.get("offer_armed")
    ):
        try:
            parts.append(load_prompt("assessment/phq9_offer"))
        except Exception as exc:  # pragma: no cover
            logger.warning("phq9_offer overlay load failed: %s", exc)

    if state.get("phq9_declined_note"):
        parts.append(
            "==================== PHQ DECLINE NOTICE ====================\n\n"
            "The user just declined the PHQ-9 mood check-in offer this turn.\n"
            "Do NOT mention the PHQ-9 again. Do NOT repeat the offer.\n"
            "Acknowledge the decline briefly and naturally (one short sentence max),\n"
            "then return to whatever topic the user was discussing before the offer.\n"
            "Use the conversation history to pick up where you left off."
        )

    phq9_reason = phq9_state.get("reason") or ""
    if phq9_state.get("phase") == "idle" and phq9_reason.startswith("suppressed:"):
        parts.append(
            "==================== PHQ SUPPRESSED NOTICE ====================\n\n"
            "The system has temporarily disabled the PHQ-9 mood assessment for this user to protect their well-being.\n"
            "If the user asks to take a mood test, mental check, or PHQ-9, you MUST gently decline.\n"
            "Do NOT administer any test questions and do NOT hallucinate the PHQ-9 process.\n"
            "Instead, acknowledge their request empathetically, explain that right now you just want to focus "
            "on listening and supporting them directly through regular conversation, and invite them to share whatever is on their mind."
        )

    if state.get("confession_mode"):
        try:
            parts.append(load_prompt("assessment/confession_mode"))
        except Exception as exc:  # pragma: no cover
            logger.warning("confession_mode overlay load failed: %s", exc)

    # Language policy: mirror the user's latest language.
    signals = state.get("linguistic_signals") or {}
    detected = (
        signals.get("language")
        if isinstance(signals, dict)
        else None
    )
    language = state.get("resolved_language") or "id"
    parts.append(
        "LANGUAGE POLICY (mandatory): Mirror the user's language. "
        "If the user used English, reply in English. If the user used Indonesian, "
        "reply in Indonesian. If the user code-switched (mixed), preserve the same "
        "natural mix and do NOT translate into a single language. "
        f"resolved_language={language}; "
        f"detected_user_language={detected or 'unknown'}."
    )

    if state.get("single_pass_voice"):
        voice = state.get("voice_state") or {}
        if voice.get("output_modality") in ("voice", "both"):
            from agentic.agent.nodes.speech_adapter import select_mode, _language_context
            from agentic.config.llm_models import SPEECH_ADAPTER, SPEECH_ADAPTER_V3
            mode = select_mode(state)
            sp_spec = SPEECH_ADAPTER_V3 if mode == "v3" else SPEECH_ADAPTER
            parts.append(
                "==================== VOICE SCRIPT MODE ENABLED ====================\n\n"
                "You are generating the FINAL SPOKEN SCRIPT directly. Do NOT write text meant only for reading.\n"
                "Apply the following speech adapter system instructions directly to your response:\n\n"
                f"{sp_spec.system_prompt}\n\n"
                "Additionally, follow the strict language context for voice:\n"
                f"{_language_context(state)}"
            )

    system_text = _SECTION_SEP.join(parts).strip()
    # print(system_text)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("response_generator system prompt:\n%s", system_text)

    messages: list[Any] = [_SystemMessage(content=system_text)]
    messages.extend(_format_history(state))
    if state.get("current_message"):
        messages.append(_HumanMessage(content=state["current_message"]))
    return messages


MAX_TOOL_ITERATIONS: int = 4
SUPPORTED_RESPONSE_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.5",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-pro",
    "gemini-3-flash",
    "gemini-3.1-flash-lite",
}


def _is_allowed_response_model(model: str) -> bool:
    if model in SUPPORTED_RESPONSE_MODELS:
        return True
    return model.startswith(
        ("gpt-", "gemini-", "mlx-", "mlx/", "mlx-community/", "lmstudio-")
    )


CONFESSION_MODE_MAX_TOKENS: int = 12000

_URL_RE = re.compile(r"https?://\S+")


async def _maybe_fetch_gemini_url_context(message: str) -> str | None:
    """Fetch page content for a URL the user shared, via Gemini's native
    ``url_context`` tool. Gemini-only (not supported by langchain_google_genai's
    bind_tools, so this bypasses LangChain and calls the google-genai SDK
    directly) — returns None on any failure so a missing key, network error,
    or non-Gemini provider never blocks the main response.
    """
    if llm_provider() != "gemini":
        return None
    if not message or not _URL_RE.search(message):
        return None
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_URL_CONTEXT_MODEL", "gemini-2.5-flash")
        response = await client.aio.models.generate_content(
            model=model,
            contents=message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
            ),
        )
        text = (getattr(response, "text", "") or "").strip()
        if not text:
            return None
        return f"URL CONTEXT (fetched via Gemini url_context tool):\n\n{text}"
    except Exception as exc:
        logger.warning("gemini url_context fetch failed: %s", exc)
        return None


def _response_generator_spec(state: ConversationState):
    model = (state.get("preferred_response_model") or "").strip()
    if not model or not _is_allowed_response_model(model):
        spec = RESPONSE_GENERATOR
    else:
        resolve_llm_model(model, spec_name=RESPONSE_GENERATOR.name)
        spec = replace(RESPONSE_GENERATOR, model=model)

    if state.get("confession_mode"):
        spec = replace(spec, max_tokens=CONFESSION_MODE_MAX_TOKENS)
    return spec


async def response_generator_node(
    state: ConversationState,
    *,
    llm: Any | None = None,
    audit: GuardrailLogger | None = None,
    tools: list | None = None,
    assessment_repo: AssessmentRepository | None = None,
) -> ConversationState:
    audit = audit or NullGuardrailLogger()

    if state.get("crisis_escalated"):  # type: ignore[typeddict-unknown-key]
        return state
    if state.get("final_response"):
        return state

    phq9_phase = (state.get("phq9_state") or {}).get("phase", "idle")
    if phq9_phase in ("offered", "in_progress", "awaiting_clar"):
        return state

    if state.get("response_draft"):
        return state

    url_context = await _maybe_fetch_gemini_url_context(state.get("current_message") or "")
    if url_context:
        state["url_context"] = url_context

    base_client = llm if llm is not None else build_llm(_response_generator_spec(state))
    bound_tools = _resolve_tools(tools)
    client = _maybe_bind_tools(base_client, bound_tools)
    tools_by_name = {t.name: t for t in bound_tools if hasattr(t, "name")} if bound_tools else {}

    messages = _build_messages(state)

    if len(messages) == 1:
        # No history and no current message. We cannot call Gemini without contents.
        # This usually happens if STT drops a hallucination on an empty audio clip.
        if (state.get("resolved_language") or "id") == "id":
            draft = "Maaf, aku tidak mendengar apa-apa. Bisa diulangi?"
        else:
            draft = "Sorry, I didn't catch that. Could you repeat?"
        tool_iterations = 0
        started = time.perf_counter()
    else:
        started = time.perf_counter()
        draft, tool_iterations = await _run_tool_loop(
            client=client,
            messages=messages,
            tools_by_name=tools_by_name,
            state=state,
            audit=audit,
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    draft = _polish_companion_style(draft)
    
    if state.get("single_pass_voice"):
        voice = dict(state.get("voice_state") or {})
        if voice.get("output_modality") in ("voice", "both"):
            from agentic.agent.nodes.speech_adapter import select_mode, _normalize_laughter, _strip_v3_tags
            mode = select_mode(state)
            adapted = _normalize_laughter(draft)
            if mode == "v3":
                voice["speech_response_tags"] = adapted
                voice["speech_response"] = _strip_v3_tags(adapted)
                # Clean the draft for the UI so it doesn't show the v3 tags
                draft = voice["speech_response"]
            else:
                voice["speech_response"] = adapted
            
            voice["tts_model"] = mode
            voice["speech_adapted_in_generator"] = True
            state["voice_state"] = voice  # type: ignore[typeddict-item]

    state["response_draft"] = draft

    phq9 = state.get("phq9_state") or {}
    if phq9.get("phase") == "offer_pending" and phq9.get("offer_armed"):
        phq9 = dict(phq9)
        phq9["phase"] = "offered"
        phq9["offer_armed"] = False
        phq9["offer_made_at_turn"] = int(state.get("session_turn") or 0)
        state["phq9_state"] = phq9  # type: ignore[typeddict-item]
        user_id = state.get("user_id") or ""
        session_id = state.get("session_id") or ""
        if assessment_repo is not None and user_id and session_id:
            try:
                await assessment_repo.save_phq9_progress(
                    user_id=user_id,
                    session_id=session_id,
                    state=phq9,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("phq9 offered-state persist failed: %s", exc)

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,
            event_type="response_generated",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=state.get("cbt_node_active"),
            latency_ms=elapsed_ms,
            metadata={
                "draft_chars": len(draft),
                "history_pairs_used": len(_format_history(state)) // 2,
                "tool_iterations": tool_iterations,
                "tools_bound": list(tools_by_name.keys()),
            },
        )
    )
    return state


def _flatten_tools(items: list) -> list:
    out = []

    for item in items:
        if isinstance(item, list):
            out.extend(_flatten_tools(item))
        else:
            out.append(item)

    return out

def _resolve_tools(tools: list | None) -> list:
    if tools is not None:
        return _flatten_tools(list(tools))
    try:
        from agentic.agent.tools import get_default_toolset

        return _flatten_tools(get_default_toolset())
    except Exception as exc:  # pragma: no cover
        logger.warning("default toolset unavailable: %s", exc)
        return []


def _maybe_bind_tools(client: Any, tools: list) -> Any:
    if not tools:
        return client
    binder = getattr(client, "bind_tools", None)
    if binder is None:
        return client
    try:
        return binder(tools)
    except Exception as exc:
        logger.warning("bind_tools failed (%s); falling back to plain client", exc)
        return client


async def _run_tool_loop(
    *,
    client: Any,
    messages: list[Any],
    tools_by_name: dict,
    state: ConversationState,
    audit: GuardrailLogger,
) -> tuple[str, int]:
    iterations = 0
    final_text = ""

    while iterations < MAX_TOOL_ITERATIONS + 1:
        try:
            ai = await client.ainvoke(messages)
            observe_langchain_usage(ai, fallback_model=getattr(client, "model_name", None))
        except Exception as exc:
            logger.warning("response generator LLM failed: %s", exc)
            return _safe_fallback_reply(state), iterations

        tool_calls = _extract_tool_calls(ai)
        if not tool_calls or not tools_by_name:
            text = ai.content if isinstance(ai.content, str) else str(ai.content)
            final_text = (text or "").strip()
            if not final_text:
                final_text = _safe_fallback_reply(state)
            return final_text, iterations

        if iterations >= MAX_TOOL_ITERATIONS:
            logger.warning("tool loop hit cap at %d iterations", iterations)
            text = ai.content if isinstance(ai.content, str) else str(ai.content)
            final_text = (text or "").strip() or _safe_fallback_reply(state)
            return final_text, iterations

        messages.append(ai)
        for call in tool_calls:
            await _invoke_tool_call(
                call=call,
                tools_by_name=tools_by_name,
                messages=messages,
                state=state,
                audit=audit,
            )
        iterations += 1

    return final_text or _safe_fallback_reply(state), iterations


def _extract_tool_calls(ai: Any) -> list[dict[str, Any]]:
    raw = getattr(ai, "tool_calls", None) or []
    out: list[dict[str, Any]] = []
    for call in raw:
        if isinstance(call, dict):
            out.append(call)
            continue
        out.append({
            "name": getattr(call, "name", ""),
            "args": getattr(call, "args", {}) or {},
            "id": getattr(call, "id", ""),
        })
    return out


async def _invoke_tool_call(
    *,
    call: dict[str, Any],
    tools_by_name: dict,
    messages: list[Any],
    state: ConversationState,
    audit: GuardrailLogger,
) -> None:
    name = call.get("name", "")
    args = call.get("args") or {}
    call_id = call.get("id") or name

    tool = tools_by_name.get(name)
    if tool is None:
        result = {"error": f"unknown_tool:{name}"}
    else:
        try:
            invoker = getattr(tool, "ainvoke", None) or getattr(tool, "invoke")
            result = invoker(args) if invoker is None else await _maybe_await(invoker, args)
        except Exception as exc:
            logger.warning("tool %s failed: %s", name, exc)
            result = {"error": str(exc)[:200]}

    messages.append(
        _ToolMessage(content=_to_str(result), tool_call_id=call_id)
    )

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,
            event_type="tool_called",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=name,
            metadata={"args": _to_str(args)[:200]},
        )
    )


async def _maybe_await(invoker: Any, args: dict[str, Any]) -> Any:
    import inspect

    out = invoker(args)
    if inspect.isawaitable(out):
        out = await out
    return out


def _to_str(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    try:
        import json

        return json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        return str(payload)


def _safe_fallback_reply(state: ConversationState) -> str:
    if (state.get("resolved_language") or "id") == "id":
        return (
            "Aku ada di sini sama kamu. Ada gangguan teknis sebentar di "
            "sisiku. Boleh ulangi yang tadi kamu ceritain?"
        )
    return (
        "I'm here with you. I had a brief hiccup on my end. Could you "
        "share that again?"
    )


__all__ = [
    "MAX_TOOL_ITERATIONS",
    "response_generator_node",
]
