"""skip error"""

from types import SimpleNamespace

import pytest

from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.nodes.response_generator import (
    _maybe_fetch_gemini_url_context,
    _run_tool_loop,
    response_generator_node,
)


class _FakeAIMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _FakeClient:
    """`minimal client`"""

    def __init__(self):
        self.bound_tools = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages):
        return _FakeAIMessage("hi there")


@pytest.mark.asyncio
async def test_response_generator_never_binds_google_search_when_gemini(monkeypatch):
    """skip gemini"""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    fake_client = _FakeClient()
    state = {"messages": [], "current_message": "halo, apa kabar?"}

    await response_generator_node(state, llm=fake_client, tools=[])

    assert {"google_search": {}} not in (fake_client.bound_tools or [])


@pytest.mark.asyncio
async def test_response_generator_never_binds_google_search_with_default_toolset(monkeypatch):
    """`skip`"""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    fake_client = _FakeClient()
    state = {"messages": [], "current_message": "halo, apa kabar?"}

    await response_generator_node(state, llm=fake_client, tools=None)

    assert fake_client.bound_tools, "default toolset should still be bound"
    assert {"google_search": {}} not in fake_client.bound_tools


@pytest.mark.asyncio
async def test_response_generator_no_google_search_when_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    fake_client = _FakeClient()
    state = {"messages": [], "current_message": "halo, apa kabar?"}

    await response_generator_node(state, llm=fake_client, tools=[])

    assert {"google_search": {}} not in (fake_client.bound_tools or [])


@pytest.mark.asyncio
async def test_tool_loop_returns_content_when_no_tool_calls_present():
    """init state"""
    client = _FakeClient()

    text, iterations = await _run_tool_loop(
        client=client,
        messages=[],
        tools_by_name={},
        state={},
        audit=NullGuardrailLogger(),
    )

    assert text == "hi there"
    assert iterations == 0


@pytest.mark.asyncio
async def test_url_context_returns_none_without_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    result = await _maybe_fetch_gemini_url_context("halo, apa kabar?")
    assert result is None


@pytest.mark.asyncio
async def test_url_context_returns_none_when_not_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    result = await _maybe_fetch_gemini_url_context("cek link ini dong https://example.com")
    assert result is None


@pytest.mark.asyncio
async def test_url_context_returns_none_without_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = await _maybe_fetch_gemini_url_context("cek https://example.com ya")
    assert result is None


class _FakeModels:
    def __init__(self, text: str):
        self._text = text

    async def generate_content(self, **kwargs):
        return SimpleNamespace(text=self._text)


class _FakeGenaiClient:
    def __init__(self, api_key=None):
        self.aio = SimpleNamespace(models=_FakeModels("Ini isi halaman contoh."))


@pytest.mark.asyncio
async def test_url_context_success(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", _FakeGenaiClient)

    result = await _maybe_fetch_gemini_url_context("liat ini dong https://example.com")

    assert result is not None
    assert "Ini isi halaman contoh." in result
    assert "url_context" in result.lower()


class _FailingModels:
    async def generate_content(self, **kwargs):
        raise RuntimeError("boom")


class _FailingGenaiClient:
    def __init__(self, api_key=None):
        self.aio = SimpleNamespace(models=_FailingModels())


@pytest.mark.asyncio
async def test_url_context_returns_none_on_exception(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", _FailingGenaiClient)

    result = await _maybe_fetch_gemini_url_context("https://example.com ini apa ya")

    assert result is None
