"""retry once on gmx's empty resp"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic.agent.nodes.text_to_speech import GeminiTTSClient
from agentic.config.voices import VoiceEntry


def _voice() -> VoiceEntry:
    return VoiceEntry(
        id="Puck",
        label_id="Puck",
        label_en="Puck",
        gender="",
        language="id",
        persona="user-selected",
        elevenlabs_voice_id="Puck",
        openai_fallback_voice="alloy",
    )


def _empty_response() -> SimpleNamespace:
    candidate = SimpleNamespace(content=None, finish_reason="OTHER")
    return SimpleNamespace(candidates=[candidate])


def _audio_response(pcm: bytes = b"\x00\x01") -> SimpleNamespace:
    part = SimpleNamespace(inline_data=SimpleNamespace(data=pcm))
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content, finish_reason="STOP")
    return SimpleNamespace(candidates=[candidate])


class _FakeGenAIClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate_content))

    async def _generate_content(self, **_kwargs):
        response = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return response


class TestGeminiTTSClientRetry:
    @pytest.mark.asyncio
    async def test_retries_once_and_recovers_from_a_transient_empty_response(self) -> None:
        fake_client = _FakeGenAIClient([_empty_response(), _audio_response()])
        client = GeminiTTSClient(client=fake_client, retry_delay_s=0)

        result = await client.synthesize(text="halo", voice=_voice(), model="gemini-3.5-flash-preview-tts")

        assert result.error is None
        assert result.audio_blob is not None
        assert fake_client.calls == 2

    @pytest.mark.asyncio
    async def test_gives_up_after_one_retry_if_still_failing(self) -> None:
        fake_client = _FakeGenAIClient([_empty_response(), _empty_response()])
        client = GeminiTTSClient(client=fake_client, retry_delay_s=0)

        result = await client.synthesize(text="halo", voice=_voice(), model="gemini-3.5-flash-preview-tts")

        assert result.error == "empty_response:OTHER"
        assert fake_client.calls == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_success(self) -> None:
        fake_client = _FakeGenAIClient([_audio_response()])
        client = GeminiTTSClient(client=fake_client, retry_delay_s=0)

        result = await client.synthesize(text="halo", voice=_voice(), model="gemini-3.5-flash-preview-tts")

        assert result.error is None
        assert fake_client.calls == 1
