"""
Regression test for the ChatGraphService optional-provider builders.

_build_stt() used to raise RuntimeError when OPENAI_API_KEY was unset,
which crashed the one-time lazy graph build (_build_graph_once) for
EVERY request -- text or voice -- in any deployment running a non-OpenAI
LLM_PROVIDER without an OpenAI key configured (e.g. production's
LLM_PROVIDER=gemini). The crash happened after the SSE response had
already started (200 OK sent), which surfaced on the Go side as
"agentic read stream: unexpected EOF" for every single chat message.

STT is optional exactly like the two TTS providers (which already
soft-fail to None) -- text-only chat never touches it at all.
"""
from __future__ import annotations

import os

import pytest

from agentic.agent.nodes.speech_to_text import (
    GeminiTranscriptionProvider,
    OpenAITranscriptionProvider,
)
from agentic.gateway.service.chat_graph import ChatGraphService


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    """Every test in this file starts from a clean slate for the env vars
    _build_stt/_build_tts_providers actually branch on."""
    for name in (
        "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY",
        "LLM_PROVIDER", "ELEVENLABS_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


class TestBuildSTT:
    def test_no_keys_at_all_returns_none_not_raise(self) -> None:
        provider = ChatGraphService._build_stt()
        assert provider is None

    def test_present_openai_key_builds_provider(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        provider = ChatGraphService._build_stt()
        assert isinstance(provider, OpenAITranscriptionProvider)

    def test_gemini_preferred_when_llm_provider_is_gemini(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        provider = ChatGraphService._build_stt()
        assert isinstance(provider, GeminiTranscriptionProvider)

    def test_openai_preferred_when_llm_provider_is_openai(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        provider = ChatGraphService._build_stt()
        assert isinstance(provider, OpenAITranscriptionProvider)

    def test_falls_back_to_whichever_key_exists_when_preferred_is_missing(
        self, monkeypatch,
    ) -> None:
        # LLM_PROVIDER=gemini but only OPENAI_API_KEY is actually set.
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        provider = ChatGraphService._build_stt()
        assert isinstance(provider, OpenAITranscriptionProvider)


class TestBuildTTSProviders:
    """Sanity check the pattern _build_stt now matches."""

    def test_missing_keys_returns_none_for_both(self) -> None:
        elevenlabs, openai_tts = ChatGraphService._build_tts_providers()
        assert elevenlabs is None
        assert openai_tts is None
