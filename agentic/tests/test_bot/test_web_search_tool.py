"""Tests for web_search, LLM_PROVIDER, provider ordering, Gemini, ground-chunk, normalizing."""
from __future__ import annotations

from types import SimpleNamespace

from agentic.agent.tools.context_awareness_tool import (
    _normalize_gemini_grounding_chunks,
    web_search,
)


def _fake_grounding_metadata(chunks):
    return SimpleNamespace(grounding_chunks=chunks)


def _fake_web_chunk(uri, title):
    return SimpleNamespace(web=SimpleNamespace(uri=uri, title=title))


class TestNormalizeGeminiGroundingChunks:
    def test_extracts_uri_and_title(self) -> None:
        metadata = _fake_grounding_metadata([
            _fake_web_chunk("https://example.com/a", "Example A"),
            _fake_web_chunk("https://example.com/b", "Example B"),
        ])
        results = _normalize_gemini_grounding_chunks(metadata)
        assert results == [
            {"title": "Example A", "url": "https://example.com/a", "content": None},
            {"title": "Example B", "url": "https://example.com/b", "content": None},
        ]

    def test_skips_chunks_with_no_web_field(self) -> None:
        metadata = _fake_grounding_metadata([SimpleNamespace(web=None)])
        assert _normalize_gemini_grounding_chunks(metadata) == []

    def test_none_metadata_returns_empty(self) -> None:
        assert _normalize_gemini_grounding_chunks(None) == []


class TestWebSearchProviderOrdering:
    def test_gemini_tried_first_when_llm_provider_is_gemini(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        calls = []

        def fake_gemini(query, max_results):
            calls.append("gemini")
            return {"query": query, "results": [{"title": "g", "url": "u", "content": None}], "source": "gemini"}

        def fake_openai(query, max_results):
            calls.append("openai")
            return {"query": query, "results": [], "error": "should not be called", "source": "openai"}

        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._gemini_web_search", fake_gemini,
        )
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._openai_web_search", fake_openai,
        )
        result = web_search.func("who won euro 2024")
        assert calls == ["gemini"]
        assert result["source"] == "gemini"

    def test_openai_tried_first_when_llm_provider_is_openai(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        calls = []

        def fake_gemini(query, max_results):
            calls.append("gemini")
            return {"query": query, "results": [], "error": "should not be called", "source": "gemini"}

        def fake_openai(query, max_results):
            calls.append("openai")
            return {"query": query, "results": [{"title": "o", "url": "u", "content": None}], "source": "openai"}

        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._gemini_web_search", fake_gemini,
        )
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._openai_web_search", fake_openai,
        )
        result = web_search.func("who won euro 2024")
        assert calls == ["openai"]
        assert result["source"] == "openai"

    def test_falls_back_to_other_provider_on_error(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        def failing_gemini(query, max_results):
            return {"query": query, "results": [], "error": "gemini down", "source": "gemini"}

        def working_openai(query, max_results):
            return {"query": query, "results": [{"title": "o", "url": "u", "content": None}], "source": "openai"}

        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._gemini_web_search", failing_gemini,
        )
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._openai_web_search", working_openai,
        )
        result = web_search.func("who won euro 2024")
        assert result["source"] == "openai"
        assert result["results"]

    def test_both_failing_surfaces_primary_error_with_fallback_noted(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        def failing_gemini(query, max_results):
            return {"query": query, "results": [], "error": "gemini down", "source": "gemini"}

        def failing_openai(query, max_results):
            return {"query": query, "results": [], "error": "openai down", "source": "openai"}

        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._gemini_web_search", failing_gemini,
        )
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._openai_web_search", failing_openai,
        )
        result = web_search.func("who won euro 2024")
        assert result["source"] == "gemini"
        assert result["error"] == "gemini down"
        assert result["fallback_error"] == "openai down"

    def test_empty_query_short_circuits_without_calling_either_provider(self, monkeypatch) -> None:
        calls = []
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._gemini_web_search",
            lambda *a: calls.append("gemini"),
        )
        monkeypatch.setattr(
            "agentic.agent.tools.context_awareness_tool._openai_web_search",
            lambda *a: calls.append("openai"),
        )
        result = web_search.func("   ")
        assert calls == []
        assert result["error"] == "empty query"
