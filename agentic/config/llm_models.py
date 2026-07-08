"""ssot LLM sel di LangGraph"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal



ReasoningEffort = Literal["low", "medium", "high"]
LLMProvider = Literal["openai", "gemini", "local"]


@dataclass(frozen=True)
class LLMSpec:
    """name: id model: model temperature: temp max_tokens: max timeout_s: timeout prompt_ref: ref reasoning_effort: effort extra_kwargs: kwargs"""

    name: str
    model: str
    temperature: float
    max_tokens: int
    prompt_ref: str
    timeout_s: float = 30.0
    reasoning_effort: ReasoningEffort | None = None
    extra_kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def system_prompt(self) -> str:
        """resolve prompt yaml lazily"""
        from agentic.prompts import load_prompt

        return load_prompt(self.prompt_ref)



_DEFAULT_CHEAP = os.getenv("LLM_MODEL_CHEAP", "gpt-4o-mini")
_DEFAULT_STRONG = os.getenv("LLM_MODEL_STRONG", "gpt-5.5")
_DEFAULT_STRONG_GENERATION = os.getenv("LLM_MODEL_STRONG_GENERATION", "gpt-5.4-nano")
_DEFAULT_KG_EXTRACTOR = os.getenv("LLM_MODEL_KG_EXTRACTOR", "o4-mini")
_DEFAULT_KG_REASONING_EFFORT: ReasoningEffort = os.getenv(  # type: ignore[assignment]
    "LLM_KG_REASONING_EFFORT", "high"
)

_GEMINI_MODEL_CHEAP = os.getenv("GEMINI_MODEL_CHEAP", "gemini-2.5-flash-lite")
_GEMINI_MODEL_STRONG = os.getenv("GEMINI_MODEL_STRONG", "gemini-2.5-flash")
_GEMINI_MODEL_STRONG_GENERATION = os.getenv(
    "GEMINI_MODEL_STRONG_GENERATION",
    _GEMINI_MODEL_STRONG,
)
_GEMINI_MODEL_KG_EXTRACTOR = os.getenv(
    "GEMINI_MODEL_KG_EXTRACTOR",
    _GEMINI_MODEL_STRONG,
)
_GEMINI_MODEL_RETRIEVAL_QUERY_REWRITER = os.getenv(
    "GEMINI_RETRIEVAL_QUERY_REWRITER_MODEL",
    _GEMINI_MODEL_CHEAP,
)

_GEMINI_CHEAP_SPEC_NAMES = {
    "phq9_scorer",
    "phq9_conversation",
    "phq9_clarification_explainer",
    "phq9_judge",
    "cbt_grounding",
    "cbt_judge",
    "speech_adapter",
    "speech_adapter_v3",
}

_GEMINI_STRONG_GENERATION_SPEC_NAMES = {"response_generator"}

_GEMINI_EXACT_MODEL_MAP = {
    "gpt-4o-mini": _GEMINI_MODEL_CHEAP,
    "gpt-4.1-nano": _GEMINI_MODEL_CHEAP,
    "gpt-4.1-mini": _GEMINI_MODEL_CHEAP,
    "gpt-5.4-nano": _GEMINI_MODEL_CHEAP,
    "gpt-5.4-mini": _GEMINI_MODEL_STRONG_GENERATION,
    "gpt-4o": _GEMINI_MODEL_STRONG_GENERATION,
    "gpt-5.5": _GEMINI_MODEL_STRONG_GENERATION,
    "o4-mini": _GEMINI_MODEL_KG_EXTRACTOR,
}

_LOCAL_MODEL_CHEAP = os.getenv(
    "LOCAL_MODEL_CHEAP",
    os.getenv("LOCAL_LLM_MODEL", "mlx-community/Qwen3-4B-Instruct-2507-4bit"),
)
_LOCAL_MODEL_STRONG = os.getenv(
    "LOCAL_MODEL_STRONG",
    os.getenv("LOCAL_LLM_MODEL", "mlx-community/Qwen3-4B-Instruct-2507-4bit"),
)
_LOCAL_MODEL_STRONG_GENERATION = os.getenv(
    "LOCAL_MODEL_STRONG_GENERATION",
    _LOCAL_MODEL_STRONG,
)
_LOCAL_MODEL_KG_EXTRACTOR = os.getenv(
    "LOCAL_MODEL_KG_EXTRACTOR",
    _LOCAL_MODEL_STRONG,
)
_LOCAL_MODEL_RETRIEVAL_QUERY_REWRITER = os.getenv(
    "LOCAL_RETRIEVAL_QUERY_REWRITER_MODEL",
    _LOCAL_MODEL_CHEAP,
)

_LOCAL_CHEAP_SPEC_NAMES = {
    "phq9_scorer",
    "phq9_conversation",
    "phq9_clarification_explainer",
    "phq9_judge",
    "cbt_grounding",
    "cbt_judge",
    "speech_adapter",
    "speech_adapter_v3",
    "retrieval_query_rewriter",
}

_LOCAL_STRONG_GENERATION_SPEC_NAMES = {"response_generator"}


def llm_provider() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider in ("", "openai"):
        return "openai"
    if provider in ("gemini", "google", "google-genai", "google_genai"):
        return "gemini"
    if provider in ("local", "mlx", "mlx-lm", "mlx_lm"):
        return "local"
    raise ValueError(
        f"Unsupported LLM_PROVIDER={provider!r}. Supported providers: openai, gemini, local."
    )


def resolve_llm_model(model: str, *, spec_name: str | None = None) -> str:
    """resolve provider-specific model ids"""
    provider = llm_provider()
    requested = (model or "").strip()
    if requested.startswith("models/gemini-"):
        requested = requested.removeprefix("models/")
    if provider == "openai":
        return requested

    if provider == "local":
        if requested.startswith(("mlx-", "mlx/", "mlx-community/", "lmstudio-")):
            return requested
        if spec_name == "kg_extractor":
            return _LOCAL_MODEL_KG_EXTRACTOR
        if spec_name == "retrieval_query_rewriter":
            return _LOCAL_MODEL_RETRIEVAL_QUERY_REWRITER
        if spec_name in _LOCAL_STRONG_GENERATION_SPEC_NAMES:
            return _LOCAL_MODEL_STRONG_GENERATION
        if spec_name in _LOCAL_CHEAP_SPEC_NAMES:
            return _LOCAL_MODEL_CHEAP
        if requested.startswith(("gpt-", "o", "gemini-")):
            return _LOCAL_MODEL_STRONG
        return requested or _LOCAL_MODEL_STRONG

    if requested.startswith("gemini-"):
        return requested

    if spec_name == "kg_extractor":
        return _GEMINI_MODEL_KG_EXTRACTOR
    if spec_name == "retrieval_query_rewriter":
        return _GEMINI_MODEL_RETRIEVAL_QUERY_REWRITER
    if spec_name in _GEMINI_STRONG_GENERATION_SPEC_NAMES:
        return _GEMINI_MODEL_STRONG_GENERATION
    if spec_name in _GEMINI_CHEAP_SPEC_NAMES:
        return _GEMINI_MODEL_CHEAP
    if requested in _GEMINI_EXACT_MODEL_MAP:
        return _GEMINI_EXACT_MODEL_MAP[requested]

    if requested.startswith(("gpt-", "o")):
        return _GEMINI_MODEL_STRONG
    return requested or _GEMINI_MODEL_STRONG



RESPONSE_GENERATOR = LLMSpec(
    name="response_generator",
    model=_DEFAULT_STRONG_GENERATION,
    temperature=1,
    max_tokens=6000,
    prompt_ref="nodes/response_generator_v2",
    extra_kwargs={"streaming": True},
)

PHQ9_SCORER = LLMSpec(
    name="phq9_scorer",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=100,
    prompt_ref="assessment/phq9_scorer",
)


PHQ9_CONVERSATION = LLMSpec(
    name="phq9_conversation",
    model=_DEFAULT_CHEAP,
    temperature=0.4,
    max_tokens=200,
    prompt_ref="assessment/phq9_conversation",
)


PHQ9_CLARIFICATION_EXPLAINER = LLMSpec(
    name="phq9_clarification_explainer",
    model=_DEFAULT_CHEAP,
    temperature=0.4,
    max_tokens=250,
    prompt_ref="assessment/phq9_clarification_explainer",
)


PHQ9_FEEDBACK = LLMSpec(
    name="phq9_feedback",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=400,
    prompt_ref="assessment/phq9_feedback",
)


PHQ9_JUDGE = LLMSpec(
    name="phq9_judge",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=200,
    prompt_ref="assessment/phq9_judge",
)





SESSION_SUMMARIZER = LLMSpec(
    name="session_summarizer",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=6000,
    prompt_ref="nodes/session_summarizer",
)


KG_EXTRACTOR = LLMSpec(
    name="kg_extractor",
    model=_DEFAULT_KG_EXTRACTOR,
    temperature=1,
    max_tokens=10000,
    prompt_ref="nodes/kg_extractor",
    reasoning_effort=_DEFAULT_KG_REASONING_EFFORT,
)


# layer 3 rewrite + ctb helpers


GUARDRAIL_REWRITE = LLMSpec(
    name="guardrail_rewrite",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=600,
    prompt_ref="guardrails/post_generation",
)


CBT_REFRAME = LLMSpec(
    name="cbt_reframe",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=300,
    prompt_ref="cbt/reframe",
)


CBT_GROUNDING = LLMSpec(
    name="cbt_grounding",
    model=_DEFAULT_CHEAP,
    temperature=0.4,
    max_tokens=200,
    prompt_ref="cbt/grounding",
)


CBT_JUDGE = LLMSpec(
    name="cbt_judge",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=200,
    prompt_ref="cbt/router_judge",
)


SYSTEM_AXIS_IDENTITY = LLMSpec(
    name="system_axis_identity",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=600,
    prompt_ref="system/axis_identity",
)


SPEECH_ADAPTER = LLMSpec(
    name="speech_adapter",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=600,
    prompt_ref="nodes/speech_adapter",
)


RETRIEVAL_QUERY_REWRITER = LLMSpec(
    name="retrieval_query_rewriter",
    model=os.getenv("RETRIEVAL_QUERY_REWRITER_MODEL", "gpt-4o-mini"),
    temperature=0.0,
    max_tokens=140,
    timeout_s=10,
    prompt_ref="nodes/retrieval_query_rewriter",
)


SPEECH_ADAPTER_V3 = LLMSpec(
    name="speech_adapter_v3",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=700,
    prompt_ref="nodes/speech_adapter_v3",
)


# limit tps
SPEECH_ADAPTER_GEMINI_TAGS = LLMSpec(
    name="speech_adapter_gemini_tags",
    model=_DEFAULT_CHEAP,
    temperature=0.0,
    max_tokens=600,
    timeout_s=8,
    prompt_ref="nodes/speech_adapter_gemini_tags",
)


# skip crisis


CRISIS_EMPATHY = LLMSpec(
    name="crisis_empathy",
    model=_DEFAULT_STRONG,
    temperature=1,
    max_tokens=300,
    prompt_ref="guardrails/crisis_empathy",
)



def build_llm(spec: LLMSpec) -> Any:
    """Construct a LangChain chat client from spec.      Import inside func, cheap import for envs w/o provider deps.      Pass `reasoning_effort` for o-series; forward `temperature`."""
    provider = llm_provider()
    model = resolve_llm_model(spec.model, spec_name=spec.name)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": spec.temperature,
            "max_tokens": spec.max_tokens,
            "timeout": spec.timeout_s,
            **spec.extra_kwargs,
        }
        if spec.reasoning_effort is not None:
            kwargs["reasoning_effort"] = spec.reasoning_effort
        return ChatOpenAI(**kwargs)

    if provider == "local":
        from langchain_openai import ChatOpenAI

        base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
        api_key = os.getenv("LOCAL_LLM_API_KEY", "not-needed")
        return ChatOpenAI(
            model=model,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            timeout=spec.timeout_s,
            base_url=base_url,
            api_key=api_key,
            **{
                key: value
                for key, value in spec.extra_kwargs.items()
                if key != "streaming"
            },
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs = {
        "model": model,
        "temperature": spec.temperature,
        "max_tokens": spec.max_tokens,
        "timeout": spec.timeout_s,
        # `skip kwarg`
        **spec.extra_kwargs,
    }
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        kwargs["google_api_key"] = api_key

    return ChatGoogleGenerativeAI(**kwargs)


__all__ = [
    "LLMSpec",
    "LLMProvider",
    "build_llm",
    "llm_provider",
    "resolve_llm_model",
    "PHQ9_SCORER",
    "PHQ9_CONVERSATION",
    "PHQ9_CLARIFICATION_EXPLAINER",
    "PHQ9_FEEDBACK",
    "PHQ9_JUDGE",
    "RESPONSE_GENERATOR",
    "SESSION_SUMMARIZER",
    "KG_EXTRACTOR",
    "GUARDRAIL_REWRITE",
    "CBT_REFRAME",
    "CBT_GROUNDING",
    "CBT_JUDGE",
    "SYSTEM_AXIS_IDENTITY",
    "SPEECH_ADAPTER",
    "SPEECH_ADAPTER_V3",
    "SPEECH_ADAPTER_GEMINI_TAGS",
    "CRISIS_EMPATHY",
    "RETRIEVAL_QUERY_REWRITER",
]
