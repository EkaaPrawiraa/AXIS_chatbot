"""gen audio gpt-4o-mini-tts"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentic.config.voices import load_voice_catalog  # noqa: E402


OPENAI_TTS_VOICES = (
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
)


SAMPLE_TEXT = (
    "Halo, aku AXIS. Aku di sini menemani kamu dengan tenang. "
    "Kita bisa pelan-pelan, satu langkah dulu."
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _extension_for(response_format: str) -> str:
    if response_format == "pcm":
        return "pcm"
    if response_format == "opus":
        return "opus"
    if response_format == "aac":
        return "aac"
    if response_format == "flac":
        return "flac"
    if response_format == "wav":
        return "wav"
    return "mp3"


async def _generate_voice(
    *,
    client: AsyncOpenAI,
    voice: str,
    model: str,
    text: str,
    instructions: str,
    response_format: str,
    output_dir: Path,
) -> Path:
    response = await client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        instructions=instructions,
        response_format=response_format,
    )
    audio = await response.aread() if hasattr(response, "aread") else response.read()
    path = output_dir / f"{model}_{voice}.{_extension_for(response_format)}"
    path.write_bytes(audio)
    return path


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate samples for all OpenAI gpt-4o-mini-tts voices."
    )
    parser.add_argument("--text", default=SAMPLE_TEXT)
    parser.add_argument("--model", default=None)
    parser.add_argument("--format", default=None, dest="response_format")
    parser.add_argument(
        "--output-dir",
        default="agentic/tmp/openai_tts_voice_samples",
        type=Path,
    )
    args = parser.parse_args()

    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / "agentic" / ".env")

    catalog = load_voice_catalog(force_reload=True)
    model = args.model or os.getenv("OPENAI_TTS_MODEL") or catalog.openai_tts_model
    response_format = (
        args.response_format
        or os.getenv("OPENAI_TTS_FORMAT")
        or catalog.openai_tts_format
        or "mp3"
    )
    instructions = (
        os.getenv("OPENAI_TTS_INSTRUCTIONS")
        or catalog.openai_tts_instructions
        or "Speak naturally in a warm, calm, conversational tone."
    )

    if model != "gpt-4o-mini-tts":
        raise SystemExit(
            f"This script is for gpt-4o-mini-tts, but model resolved to {model!r}."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    client = AsyncOpenAI()

    instructions="""Speak naturally in the same language as the input text. If the input is
    Indonesian, use warm conversational Indonesian. If the input is English,
    use warm conversational English. If the input mixes both, keep the same
    language mix without translating. Use natural pacing (like human conversation), clear articulation,
    and an empathetic tone. You MUST NOT sounding robotic, formal, and theatrical."""
    # nyebutin bahasa
    for voice in OPENAI_TTS_VOICES:
        path = await _generate_voice(
            client=client,
            voice=voice,
            model=model,
            text=args.text,
            instructions=instructions,
            response_format=response_format,
            output_dir=args.output_dir,
        )
        print(f"{voice:8s} -> {path}")


if __name__ == "__main__":
    asyncio.run(main())
