import importlib


def _reload_llm_models(monkeypatch, provider: str, **env):
    for key in (
        "LLM_PROVIDER",
        "GOOGLE_API_KEY",
        "LOCAL_LLM_MODEL",
        "LOCAL_MODEL_CHEAP",
        "LOCAL_MODEL_STRONG",
        "LOCAL_MODEL_STRONG_GENERATION",
        "LOCAL_MODEL_KG_EXTRACTOR",
        "LOCAL_RETRIEVAL_QUERY_REWRITER_MODEL",
        "GEMINI_RESPONSE_GENERATOR_THINKING_BUDGET",
        "GEMINI_RESPONSE_GENERATOR_INCLUDE_THOUGHTS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", provider)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import agentic.config.llm_models as llm_models

    return importlib.reload(llm_models)


def test_openai_provider_preserves_openai_model_names(monkeypatch):
    llm_models = _reload_llm_models(monkeypatch, "openai")

    assert (
        llm_models.resolve_llm_model("gpt-4o-mini", spec_name="phq9_judge")
        == "gpt-4o-mini"
    )
    assert (
        llm_models.resolve_llm_model("o4-mini", spec_name="kg_extractor")
        == "o4-mini"
    )


def test_gemini_provider_maps_roles_to_gemini_tiers(monkeypatch):
    llm_models = _reload_llm_models(monkeypatch, "gemini")

    assert (
        llm_models.resolve_llm_model("gpt-5.4-nano", spec_name="response_generator")
        == "gemini-3.5-flash"
    )
    assert (
        llm_models.resolve_llm_model("gpt-4o-mini", spec_name="phq9_judge")
        == "gemini-3.1-flash-lite"
    )
    assert (
        llm_models.resolve_llm_model("o4-mini", spec_name="kg_extractor")
        == "gemini-3.5-flash"
    )
    assert (
        llm_models.resolve_llm_model(
            "gpt-4.1-nano",
            spec_name="retrieval_query_rewriter",
        )
        == "gemini-3.1-flash-lite"
    )


def test_gemini_provider_strips_google_model_prefix(monkeypatch):
    llm_models = _reload_llm_models(monkeypatch, "gemini")

    assert (
        llm_models.resolve_llm_model(
            "models/gemini-3.5-flash",
            spec_name="response_generator",
        )
        == "gemini-3.5-flash"
    )


def test_gemini_provider_preserves_explicit_gemini_model(monkeypatch):
    llm_models = _reload_llm_models(monkeypatch, "gemini")

    assert (
        llm_models.resolve_llm_model(
            "gemini-3.5-flash",
            spec_name="response_generator",
        )
        == "gemini-3.5-flash"
    )


def test_local_provider_maps_remote_models_to_local_tiers(monkeypatch):
    llm_models = _reload_llm_models(
        monkeypatch,
        "local",
        LOCAL_MODEL_CHEAP="mlx-community/Qwen3-4B-Instruct-2507-4bit",
        LOCAL_MODEL_STRONG="mlx-community/Qwen3-4B-Instruct-2507-4bit",
        LOCAL_MODEL_STRONG_GENERATION="mlx-community/Qwen3-4B-Instruct-2507-4bit",
    )

    assert (
        llm_models.resolve_llm_model("gpt-5.4-nano", spec_name="response_generator")
        == "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    )
    assert (
        llm_models.resolve_llm_model("gpt-4o-mini", spec_name="phq9_judge")
        == "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    )
    assert (
        llm_models.resolve_llm_model("gemini-2.5-pro", spec_name="kg_extractor")
        == "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    )


def test_local_provider_preserves_explicit_mlx_model(monkeypatch):
    llm_models = _reload_llm_models(monkeypatch, "local")

    assert (
        llm_models.resolve_llm_model(
            "mlx-community/Qwen3-4B-Instruct-2507-4bit",
            spec_name="response_generator",
        )
        == "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    )


def test_gemini_provider_forwards_extra_kwargs_like_streaming(monkeypatch):
    """extra_kwargs["streaming"] = True"""
    llm_models = _reload_llm_models(monkeypatch, "gemini", GOOGLE_API_KEY="test-key")

    import langchain_google_genai

    captured = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI
    )

    llm_models.build_llm(llm_models.RESPONSE_GENERATOR)

    assert captured.get("streaming") is True


def test_gemini_response_generator_enables_thinking_without_exposing_thoughts(monkeypatch):
    llm_models = _reload_llm_models(
        monkeypatch,
        "gemini",
        GOOGLE_API_KEY="test-key",
        GEMINI_RESPONSE_GENERATOR_THINKING_BUDGET="2048",
    )

    import langchain_google_genai

    captured = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI
    )

    llm_models.build_llm(llm_models.RESPONSE_GENERATOR)

    assert captured["thinking_budget"] == 2048
    assert captured["include_thoughts"] is False


def test_gemini_response_generator_can_disable_thinking(monkeypatch):
    llm_models = _reload_llm_models(
        monkeypatch,
        "gemini",
        GOOGLE_API_KEY="test-key",
        GEMINI_RESPONSE_GENERATOR_THINKING_BUDGET="0",
    )

    import langchain_google_genai

    captured = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI
    )

    llm_models.build_llm(llm_models.RESPONSE_GENERATOR)

    assert "thinking_budget" not in captured
    assert captured["include_thoughts"] is False


def test_response_generator_visible_text_skips_gemini_thinking_blocks():
    from agentic.agent.nodes.response_generator import _visible_ai_text

    class FakeResponse:
        content = [
            {"type": "thinking", "thinking": "hidden reasoning must not leak"},
            {"type": "text", "text": "Jawaban final untuk user."},
        ]

    assert _visible_ai_text(FakeResponse()) == "Jawaban final untuk user."
