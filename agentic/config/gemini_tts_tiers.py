"""
Gemini TTS tier -> (model id, per-gender prebuilt voice name) mapping.

Voice pairing per tier is a deliberate user choice (tested by ear in
Google AI Studio), not derived from Google's own docs -- the official
docs only describe each of the 30 prebuilt voices with a single
character adjective (e.g. "Puck: Upbeat"), with no gender attached.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiTTSTier:
    model: str
    female_voice: str
    male_voice: str
    label: str


GEMINI_TTS_TIERS: dict[str, GeminiTTSTier] = {
    "gemini-3.1-flash-tts-preview": GeminiTTSTier(
        model="gemini-3.1-flash-tts-preview",
        female_voice="Puck",
        male_voice="Fenrir",
        label="Respons suara paling gesit",
    ),
    "gemini-2.5-pro-preview-tts": GeminiTTSTier(
        model="gemini-2.5-pro-preview-tts",
        female_voice="Aoede",
        male_voice="Enceladus",
        label="Suara lebih alami dan nyaman didengar",
    ),
    "gemini-2.5-flash-preview-tts": GeminiTTSTier(
        model="gemini-2.5-flash-preview-tts",
        female_voice="Leda",
        male_voice="Charon",
        label="Konfigurasi default",
    ),
}

DEFAULT_GEMINI_TTS_TIER = "gemini-2.5-flash-preview-tts"

# The full set of Gemini prebuilt voice names (case-insensitive; Google's
# API itself returns them lowercase in error messages, but accepts the
# PascalCase spellings used elsewhere in this codebase, e.g. "Puck").
# Used to tell apart a deliberately-picked Gemini voice character (from
# the Settings picker) from some OTHER provider's voice id -- e.g.
# "alloy", ElevenLabs/OpenAI's own default -- that merely isn't a known
# catalog persona either. Passing the latter straight through to Gemini
# as if it were a real voice name gets rejected outright.
GEMINI_PREBUILT_VOICE_NAMES: frozenset[str] = frozenset({
    "achernar", "achird", "algenib", "algieba", "alnilam", "aoede",
    "autonoe", "callirrhoe", "charon", "despina", "enceladus", "erinome",
    "fenrir", "gacrux", "iapetus", "kore", "laomedeia", "leda", "orus",
    "puck", "pulcherrima", "rasalgethi", "sadachbia", "sadaltager",
    "schedar", "sulafat", "umbriel", "vindemiatrix", "zephyr",
    "zubenelgenubi",
})


def is_gemini_prebuilt_voice_name(voice_id: str | None) -> bool:
    return bool(voice_id) and voice_id.strip().lower() in GEMINI_PREBUILT_VOICE_NAMES

# Older/looser tier id spellings a client might still send (the exact
# ids without "-preview" suffixed in the middle) -- accepted so a
# slightly-off client value still resolves instead of silently falling
# back to the default tier.
_TIER_ALIASES: dict[str, str] = {
    "gemini-3.1-flash-tts": "gemini-3.1-flash-tts-preview",
    "gemini-2.5-pro-tts": "gemini-2.5-pro-preview-tts",
    "gemini-2.5-flash-tts": "gemini-2.5-flash-preview-tts",
}


def resolve_gemini_tier(tts_model: str | None) -> GeminiTTSTier:
    """Resolve a requested tier id to its GeminiTTSTier, defaulting when unknown."""
    key = _TIER_ALIASES.get(tts_model or "", tts_model or "")
    return GEMINI_TTS_TIERS.get(key, GEMINI_TTS_TIERS[DEFAULT_GEMINI_TTS_TIER])


def resolve_gemini_voice_name(tier: GeminiTTSTier, gender: str | None) -> str:
    """Female is the default when gender is missing/unrecognized."""
    return tier.male_voice if gender == "pria" else tier.female_voice


# "Karakter Suara" (voice character) picker on the profile page -- see
# VOICE_CHARACTER_MAP in frontend_v2/app/profile/page.tsx, which this
# mirrors exactly (character x gender -> real Gemini prebuilt voice
# name). Kept in sync manually; if one changes, change the other.
# Independent of GEMINI_TTS_TIERS above: tier controls latency/quality
# (which of the 3 TTS models is called), character controls WHICH voice
# speaks -- see the profile page's own comment on why these are two
# orthogonal axes, not one derived from the other.
VOICE_CHARACTER_MAP: dict[str, dict[str, str]] = {
    "hangat": {"female": "Sulafat", "male": "Achird"},
    "tenang": {"female": "Aoede", "male": "Enceladus"},
    "ceria": {"female": "Puck", "male": "Fenrir"},
    "perangkat": {"female": "Leda", "male": "Charon"},
}

_VOICE_NAME_TO_CHARACTER: dict[str, str] = {
    voice_name.lower(): character
    for character, genders in VOICE_CHARACTER_MAP.items()
    for voice_name in genders.values()
}


def resolve_voice_character(voice_id: str | None) -> str | None:
    """Reverse-lookup which of the 4 voice characters a resolved Gemini
    voice NAME belongs to (e.g. "Sulafat" -> "hangat"), or None if it
    isn't one of the 8 character x gender voices (e.g. an old catalog
    persona's tier-default fallback voice)."""
    if not voice_id:
        return None
    return _VOICE_NAME_TO_CHARACTER.get(voice_id.strip().lower())


# Director's Notes content per character -- see
# https://ai.google.dev/gemini-api/docs/speech-generation, which
# recommends steering Gemini TTS delivery via a Style/Accent/Pacing
# block rather than discrete parameters (none exist). Each description
# is deliberately about vocal DELIVERY only (how it sounds), not content
# (what it says) -- content/wording is the speech adapter's job.
_CHARACTER_STYLE_NOTES: dict[str, dict[str, str]] = {
    "hangat": {
        "style": (
            "Warm, tender, and deeply caring -- like a close friend who "
            "listens without judgment and makes people feel safe."
        ),
        "pacing": "Slow and unhurried, with soft natural pauses that give room for feelings.",
    },
    "tenang": {
        "style": (
            "Calm, steady, and grounded -- a reassuring, therapist-like "
            "presence that never sounds rushed or alarmed."
        ),
        "pacing": "Slow, deliberate, and even, with minimal pitch variation.",
    },
    "ceria": {
        "style": "Upbeat, bright, and playful -- like a cheerful close friend catching up over coffee.",
        "pacing": "Natural to brisk, with light, genuine energy.",
    },
    "perangkat": {
        "style": "Clear, neutral, and professional -- an informative assistant tone with no dramatic emotion.",
        "pacing": "Even and measured, straightforward delivery.",
    },
}
_DEFAULT_CHARACTER = "tenang"

_ACCENT_NOTE = (
    "Neutral, standard pronunciation for whichever language is being "
    "spoken (Indonesian or English) -- no exaggerated regional dialect."
)

_EMPATHETIC_MODIFIER = (
    "Right now, prioritize gentleness above all else: slow down further, "
    "soften your tone, and give the user your full, undivided, unhurried "
    "attention -- this moment calls for care over your usual energy."
)


def build_gemini_director_notes(character_id: str | None, *, empathetic: bool) -> str:
    """Build the Style/Accent/Pacing Director's Notes block Gemini TTS
    reads as plain text prepended to what it speaks (see GeminiTTSClient
    .synthesize). ``character_id`` is resolved via
    ``resolve_voice_character`` and falls back to a neutral default when
    the active voice isn't one of the 4 known characters (e.g. an old
    catalog persona resolving to a tier-default voice)."""
    style = _CHARACTER_STYLE_NOTES.get(character_id or "", _CHARACTER_STYLE_NOTES[_DEFAULT_CHARACTER])
    lines = [
        "### DIRECTOR'S NOTES",
        f"Style: {style['style']}",
        f"Accent: {_ACCENT_NOTE}",
        f"Pacing: {style['pacing']}",
    ]
    if empathetic:
        lines.append(_EMPATHETIC_MODIFIER)
    return "\n".join(lines)


__all__ = [
    "GeminiTTSTier",
    "GEMINI_TTS_TIERS",
    "DEFAULT_GEMINI_TTS_TIER",
    "GEMINI_PREBUILT_VOICE_NAMES",
    "VOICE_CHARACTER_MAP",
    "resolve_gemini_tier",
    "resolve_gemini_voice_name",
    "is_gemini_prebuilt_voice_name",
    "resolve_voice_character",
    "build_gemini_director_notes",
]
