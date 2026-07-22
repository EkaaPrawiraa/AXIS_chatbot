"""skip error"""
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
    """build_stt, build_tts, env_vars, clean, branch."""
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
        # set LLM_PROVIDER to gemini
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        provider = ChatGraphService._build_stt()
        assert isinstance(provider, OpenAITranscriptionProvider)


class TestBuildTTSProviders:
    """check sanity"""

    def test_missing_keys_returns_none_for_both(self) -> None:
        elevenlabs, openai_tts = ChatGraphService._build_tts_providers()
        assert elevenlabs is None
        assert openai_tts is None
