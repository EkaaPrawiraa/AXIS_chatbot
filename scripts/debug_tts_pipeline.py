"""Trace the real TTS pipeline end-to-end against the live Gemini API.

Runs the exact production code path (GeminiTTSClient.synthesize ->
run_tts_fallback_chain) locally and prints what goes IN to Gemini
(model, voice, text/instructions), what comes back RAW from Gemini
(candidate count, finish_reason, part count, PCM byte length), and
what would ultimately be served to the frontend (audio_output_base64
length, format) -- so a real failure/success can be inspected stage by
stage instead of guessed at.

Usage: python3 scripts/debug_tts_pipeline.py [voice_name] [model] [rounds]
Example: python3 scripts/debug_tts_pipeline.py Puck gemini-2.5-flash-preview-tts 5
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agentic"))

from dotenv import load_dotenv  # type: ignore[import-not-found]

load_dotenv(Path(__file__).resolve().parent.parent / "agentic" / ".env")

from agentic.agent.nodes.text_to_speech import GeminiTTSClient  # noqa: E402
from agentic.config.voices import VoiceEntry  # noqa: E402


class TracingGenAIClient:
    """Wraps the real google.genai client, printing request/response at each call."""

    def __init__(self) -> None:
        from google import genai  # type: ignore[import-not-found]

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._real = genai.Client(api_key=api_key)
        self.aio = self

    class _Models:
        pass

    def __getattr__(self, item):
        if item == "models":
            return self
        raise AttributeError(item)

    async def generate_content(self, *, model, contents, config):
        voice_name = config.speech_config.voice_config.prebuilt_voice_config.voice_name
        print(f"  -> SENT to Gemini: model={model!r} voice={voice_name!r} text={contents[:80]!r}...")
        response = await self._real.aio.models.generate_content(model=model, contents=contents, config=config)
        candidates = response.candidates or []
        if not candidates:
            print("  <- RECEIVED: no candidates at all")
            return response
        cand = candidates[0]
        finish_reason = getattr(cand, "finish_reason", None)
        parts = cand.content.parts if cand.content else None
        if not parts:
            print(f"  <- RECEIVED: finish_reason={finish_reason} content/parts=None (EMPTY)")
            return response
        pcm = parts[0].inline_data.data
        print(f"  <- RECEIVED: finish_reason={finish_reason} pcm_bytes={len(pcm) if pcm else 0}")
        return response


async def main() -> None:
    voice_name = sys.argv[1] if len(sys.argv) > 1 else "Puck"
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash-preview-tts"
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    voice = VoiceEntry(
        id=voice_name,
        label_id=voice_name,
        label_en=voice_name,
        gender="",
        language="id",
        persona="user-selected",
        elevenlabs_voice_id=voice_name,
        openai_fallback_voice="alloy",
    )

    for i in range(1, rounds + 1):
        print(f"\n=== round {i}/{rounds}: voice={voice_name} model={model} ===")
        tracing_client = TracingGenAIClient()
        client = GeminiTTSClient(client=tracing_client, retry_delay_s=0.6)
        result = await client.synthesize(text="Hai, aku AXIS. Aku di sini siap dengerin kamu.", voice=voice, model=model)
        if result.error:
            print(f"  ==> FINAL RESULT (what frontend would get): error={result.error!r}")
        else:
            blob_len = len(result.audio_blob) if result.audio_blob else 0
            print(f"  ==> FINAL RESULT (what frontend would get): audio_format={result.audio_format!r} wav_bytes={blob_len}")
        if i < rounds:
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
