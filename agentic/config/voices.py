"""load vlist"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml


def _env_default_language() -> str | None:
    """`lang diambil`"""
    val = os.getenv("DEFAULT_USER_LANGUAGE")
    return val.strip().lower() if val else None


_DEFAULT_PATH = Path(__file__).resolve().parent / "voices.yaml"


@dataclass(frozen=True)
class VoiceEntry:
    id: str
    label_id: str
    label_en: str
    gender: str
    language: str
    persona: str
    elevenlabs_voice_id: str
    openai_fallback_voice: str
    notes: str = ""

    @property
    def is_configured(self) -> bool:
        """filled"""
        return not self.elevenlabs_voice_id.startswith("REPLACE_WITH")


@dataclass(frozen=True)
class VoiceCatalog:
    default_voice: str
    default_voice_by_language: Mapping[str, str]
    voices: Mapping[str, VoiceEntry]
    fallback_on_quota: str
    fallback_on_failure: str
    openai_tts_model: str
    openai_tts_format: str
    openai_tts_instructions: str

    def for_language(self, language: str) -> tuple[VoiceEntry, ...]:
        """ambil suara semua"""
        return tuple(v for v in self.voices.values() if v.language == language)

    def default_for(self, language: str | None) -> VoiceEntry:
        """set_voice('en')"""
        candidates = [language, _env_default_language()]
        for cand in candidates:
            if not cand:
                continue
            mapped = self.default_voice_by_language.get(cand)
            if mapped and mapped in self.voices:
                return self.voices[mapped]
        return self.voices[self.default_voice]

    def get(
        self,
        voice_id: str | None,
        *,
        language: str | None = None,
    ) -> VoiceEntry:
        """prioritaskan 1-4"""
        if voice_id and voice_id in self.voices:
            return self.voices[voice_id]
        if voice_id:
            fallback = self.default_for(language)
            return VoiceEntry(
                id=voice_id,
                label_id=voice_id,
                label_en=voice_id,
                gender="",
                language=language or fallback.language,
                persona="user-selected",
                elevenlabs_voice_id=voice_id,
                openai_fallback_voice=fallback.openai_fallback_voice,
                notes="Resolved from provider voice id.",
            )
        return self.default_for(language)


_CACHE: VoiceCatalog | None = None


def load_voice_catalog(
    path: Path | None = None,
    *,
    force_reload: bool = False,
) -> VoiceCatalog:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    target = path or _DEFAULT_PATH
    with target.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_voices = data.get("voices") or {}
    voices: dict[str, VoiceEntry] = {}
    for vid, body in raw_voices.items():
        voices[vid] = VoiceEntry(
            id=vid,
            label_id=str(body.get("label_id", vid)),
            label_en=str(body.get("label_en", vid)),
            gender=str(body.get("gender", "")),
            language=str(body.get("language", "id")),
            persona=str(body.get("persona", "")),
            elevenlabs_voice_id=str(body.get("elevenlabs_voice_id", "")),
            openai_fallback_voice=str(body.get("openai_fallback_voice", "cedar")),
            notes=str(body.get("notes", "")),
        )

    default_voice = str(data.get("default_voice", next(iter(voices))))
    raw_lang_defaults = data.get("default_voice_by_language") or {}
    default_by_lang: dict[str, str] = {}
    for lang, vid in raw_lang_defaults.items():
        if vid in voices:
            default_by_lang[str(lang)] = str(vid)

    fallback = data.get("fallback") or {}
    catalog = VoiceCatalog(
        default_voice=default_voice,
        default_voice_by_language=default_by_lang,
        voices=voices,
        fallback_on_quota=str(fallback.get(
            "on_elevenlabs_quota_exceeded", "openai_tts1"
        )),
        fallback_on_failure=str(fallback.get(
            "on_all_failed", "text_only"
        )),
        openai_tts_model=str(fallback.get(
            "openai_tts_model", "gpt-4o-mini-tts"
        )),
        openai_tts_format=str(fallback.get("openai_tts_format", "mp3")),
        openai_tts_instructions=str(
            fallback.get("openai_tts_instructions", "")
        ).strip(),
    )
    _CACHE = catalog
    return catalog


__all__ = [
    "VoiceCatalog",
    "VoiceEntry",
    "load_voice_catalog",
]
