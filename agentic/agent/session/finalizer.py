"""finalize idle session"""

from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from agentic.assessment.phq9 import (
    ITEMS_EN,
    ITEMS_ID,
    OPTION_LABELS_EN,
    OPTION_LABELS_ID,
)

# sliding window" 6 = 3 full turns
_CONTEXT_WINDOW_MSGS = 6

_LOW_SIGNAL_EXACT = {
    "hi", "halo", "hai", "hey", "hello", "hei",
    "ok", "oke", "iya", "ya", "yep", "yap", "sip",
    "makasih", "terima kasih", "thanks", "thank you",
    "hmm", "oh", "ooh", "wah", "ah", "ehm", "huh",
}

_APP_PROBE_PATTERNS = (
    r"\bdebug\b",
    r"\btest(?:ing)?\b",
    r"\btes\s+(?:mood|suasana hati|phq|fitur|chip|button)\b",
    r"\bphq[-\s]?9\b",
    r"\bkuesioner\b",
    r"\bapa yang (?:kamu|axis) ingat\b",
    r"\bapa saja yang .*cerita(?:kan)?(?: sebelumnya)?\b",
    r"\bpernah .*cerita(?:kan)? sebelumnya\b",
    r"\b(?:asisten|assistant|axis).*(?:mengingat|remembered|ingatkan)\b",
    r"\b(?:asisten|assistant|axis).*(?:bisa apa|kemampuan|mampu)\b",
    r"\bobrolan sebelumnya\b",
    r"\b(?:suara|voice).*(?:kedengeran|terdengar|masuk)\b",
    r"\b(?:nggak|gak|ga|tidak) ada hal spesifik\b",
    r"\bbelum ada peristiwa\b",
    r"\bsotoy\b",
    r"\b(?:lu|kamu|axis).*(?:simpan|catat|ingat).*(?:data|tentang)\b",
    r"\b(?:frontend|backend|database|localhost|ui|bug|error)\b",
)

_GENERIC_REQUEST_PATTERNS = (
    r"\b(?:cari|carikan|rekomendasi|rekomendasikan)\b.*\b(?:film|movie|lagu|musik|game)\b",
    r"\b(?:nebak|tebak|nyanyi|lagu|song)\b",
    r"\b(?:buat|bikin|bikinin).*\b(?:teks|caption|tren|trend)\b",
    r"\b(?:apa itu|jelaskan|explain|gimana cara|bagaimana cara)\b",
)

_PERSONAL_SIGNAL_PATTERNS = (
    r"\baku\b.*\b(?:sedih|cemas|takut|marah|malu|capek|lelah|panik|kesepian|tertekan|gagal|dibully|dihina|ditolak)\b",
    r"\bsaya\b.*\b(?:sedih|cemas|takut|marah|malu|capek|lelah|panik|kesepian|tertekan|gagal|dibully|dihina|ditolak)\b",
    r"\b(?:teman|keluarga|ibu|ayah|dosen|pacar|kuliah|ujian|tugas|skripsi|kampus)\b",
    r"\b(?:tidak|nggak|ga|gak)\s+(?:berguna|punya teman|bisa tidur|mau hidup)\b",
    r"\b(?:ingin|mau)\s+(?:menyakiti diri|mati|menghilang)\b",
)

_PHQ9_STRUCTURAL_PATTERNS = (
    r"\bphq[-\s]?9\b",
    r"\btes\s+(?:mood|suasana hati)\b",
    r"\bkuesioner\b",
    r"\bpertanyaan\s+\d+\s+(?:dari|/)\s*9\b",
    r"\bquestion\s+\d+\s+(?:of|/)\s*9\b",
    r"\bdalam\s+2\s+minggu\s+terakhir\b",
    r"\bover\s+the\s+last\s+2\s+weeks\b",
    r"\bskor\s+total\b.*\b(?:phq|skrining|rentang)\b",
    r"\btotal\s+score\b.*\b(?:phq|screening|range)\b",
)

def _normalize_message_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


import json as _json

def _sanitize_summary(raw: str) -> str:
    """strip json wrapper"""
    stripped = raw.strip()
    if not stripped or stripped in ("{}", "SKIP", "skip"):
        return ""
    if stripped.startswith("{"):
        try:
            data = _json.loads(stripped)
            for key in ("summary", "text", "content", "result"):
                if isinstance(data.get(key), str) and data[key].strip():
                    return data[key].strip()
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, str) and len(val) > 10:
                        return val.strip()
        except (_json.JSONDecodeError, Exception):
            pass
    return stripped


_PHQ9_ITEM_TEXTS = tuple(
    _normalize_message_text(item).rstrip(".")
    for item in (*ITEMS_ID, *ITEMS_EN)
)
_PHQ9_OPTION_LABELS = {
    _normalize_message_text(label)
    for label in (*OPTION_LABELS_ID, *OPTION_LABELS_EN)
}
_PHQ9_OPTION_LABELS.update({"0", "1", "2", "3"})


def _looks_like_app_probe(text: str) -> bool:
    normalized = _normalize_message_text(text)
    if not normalized:
        return True
    return any(re.search(pattern, normalized) for pattern in _APP_PROBE_PATTERNS)


def _has_personal_memory_signal(text: str) -> bool:
    normalized = _normalize_message_text(text)
    if len(normalized) < 18:
        return False
    return any(re.search(pattern, normalized) for pattern in _PERSONAL_SIGNAL_PATTERNS)


def _should_skip_memory_extraction(text: str) -> bool:
    normalized = _normalize_message_text(text)
    if not normalized or normalized in _LOW_SIGNAL_EXACT:
        return True
    if _looks_like_app_probe(normalized) and not _has_personal_memory_signal(normalized):
        return True
    if (
        any(re.search(pattern, normalized) for pattern in _GENERIC_REQUEST_PATTERNS)
        and not _has_personal_memory_signal(normalized)
    ):
        return True
    return False


def _metadata_dict(raw: Any) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _looks_like_phq9_prompt_or_feedback(text: str) -> bool:
    normalized = _normalize_message_text(text)
    if not normalized:
        return False
    if any(re.search(pattern, normalized) for pattern in _PHQ9_STRUCTURAL_PATTERNS):
        return True
    stripped = normalized.rstrip(".")
    return any(item in stripped for item in _PHQ9_ITEM_TEXTS)


def _looks_like_phq9_answer(text: str) -> bool:
    normalized = _normalize_message_text(text)
    if not normalized:
        return False
    if normalized in _PHQ9_OPTION_LABELS:
        return True
    # nto PHQ
    return any(
        normalized.startswith(f"{label} ")
        for label in _PHQ9_OPTION_LABELS
        if not label.isdigit()
    )


def _has_phq9_metadata(msg: Mapping[str, Any]) -> bool:
    metadata = _metadata_dict(msg.get("metadata"))
    if "phq9" in metadata:
        return True
    state = metadata.get("phq9_state")
    if isinstance(state, Mapping):
        return True
    return False


def _is_phq9_message(
    msg: Mapping[str, Any],
    *,
    previous_assistant_was_phq9: bool = False,
) -> bool:
    content = (msg.get("content") or "").strip()
    if not content:
        return False
    if _has_phq9_metadata(msg):
        return True
    if _looks_like_phq9_prompt_or_feedback(content):
        return True
    if msg.get("role") == "user" and previous_assistant_was_phq9:
        return _looks_like_phq9_answer(content) or len(_normalize_message_text(content)) < 80
    return False


logger = logging.getLogger(__name__)


class HistoryLoader:
    async def __call__(
        self,
        *,
        session_id: str,
        user_id: str,
        after_turn_index: int | None = None,
        through_turn_index: int | None = None,
    ) -> Sequence[Mapping[str, Any]]:
        ...


class SessionMetadataLoaderFn:
    """load sess data"""
    async def __call__(
        self, *, session_id: str, user_id: str,
    ) -> Mapping[str, Any]:
        ...


class UserContextLoaderFn:
    """load ctx"""
    async def __call__(
        self, *, user_id: str,
    ) -> Mapping[str, Any]:
        ...


class SummarizerFn:
    async def __call__(
        self,
        *,
        transcript: str,
        language: str | None,
        session_metadata: Mapping[str, Any] | None = None,
    ) -> str:
        ...


class KGExtractorFn:
    async def __call__(
        self,
        *,
        message: str,
        user_id: str,
        session_id: str,
        language: str | None,
        preceding_context: list[dict[str, str]] | None = None,
        session_metadata: Mapping[str, Any] | None = None,
        user_kg_context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ...


class KGWriterFn:
    async def __call__(
        self,
        *,
        user_id: str,
        session_id: str,
        summary: str,
        extracted: Sequence[Mapping[str, Any]],
        language: str | None,
    ) -> None:
        ...


@dataclass
class FinalizationResult:
    session_id: str
    summary: str
    extracted_count: int
    processed_count: int = 0
    through_turn_index: int | None = None
    error: str | None = None
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class SessionFinalizer:
    history_loader: HistoryLoader
    summarizer: SummarizerFn
    extractor: KGExtractorFn
    kg_writer: KGWriterFn
    session_metadata_loader: SessionMetadataLoaderFn | None = None
    user_context_loader: UserContextLoaderFn | None = None

    async def finalize(
        self,
        *,
        session_id: str,
        user_id: str,
        language: str | None = None,
        after_turn_index: int | None = None,
        through_turn_index: int | None = None,
    ) -> FinalizationResult:

        try:
            try:
                history = await self.history_loader(
                    session_id=session_id,
                    user_id=user_id,
                    after_turn_index=after_turn_index,
                    through_turn_index=through_turn_index,
                )
            except TypeError:
                history = await self.history_loader(
                    session_id=session_id, user_id=user_id,
                )
        except Exception as exc:
            logger.exception("history loader failed: %s", exc)
            return FinalizationResult(
                session_id=session_id,
                summary="",
                extracted_count=0,
                through_turn_index=through_turn_index,
                error=f"history_loader:{exc}",
            )

        if not history:
            return FinalizationResult(
                session_id=session_id,
                summary="",
                extracted_count=0,
                processed_count=0,
                through_turn_index=through_turn_index,
            )

        memory_history = _filter_phq9_messages(history)

        process_history = [
            msg for msg in memory_history
            if _in_processing_range(
                msg,
                after_turn_index=after_turn_index,
                through_turn_index=through_turn_index,
            )
        ]
        if not process_history:
            return FinalizationResult(
                session_id=session_id,
                summary="",
                extracted_count=0,
                processed_count=0,
                through_turn_index=through_turn_index,
            )

        user_messages_in_range = [
            (msg.get("content") or "").strip()
            for msg in process_history
            if msg.get("role") == "user" and (msg.get("content") or "").strip()
        ]
        has_substantive_memory = any(
            not _should_skip_memory_extraction(content)
            for content in user_messages_in_range
        )

        session_metadata: Mapping[str, Any] = {}
        if self.session_metadata_loader is not None:
            try:
                session_metadata = await self.session_metadata_loader(
                    session_id=session_id, user_id=user_id,
                )
            except Exception as exc:
                logger.warning(
                    "session_metadata_loader failed (session=%s): %s - continuing without metadata",
                    session_id, exc,
                )

        user_kg_context: Mapping[str, Any] = {}
        if self.user_context_loader is not None:
            try:
                user_kg_context = await self.user_context_loader(user_id=user_id)
            except Exception as exc:
                logger.warning(
                    "user_context_loader failed (user=%s): %s - continuing without KG context",
                    user_id, exc,
                )

        if has_substantive_memory:
            transcript = _format_transcript(memory_history)
            try:
                summary = await self.summarizer(
                    transcript=transcript,
                    language=language,
                    session_metadata=session_metadata or None,
                )
                summary = _sanitize_summary(summary)
            except Exception as exc:
                logger.exception("summarizer failed: %s", exc)
                return FinalizationResult(
                    session_id=session_id,
                    summary="",
                    extracted_count=0,
                    processed_count=len(process_history),
                    through_turn_index=through_turn_index,
                    error=f"summarizer:{exc}",
                )
        else:
            summary = ""
            logger.info(
                "session_finalizer: skipped summary for low-signal session "
                "(user=%s session=%s messages=%d)",
                user_id, session_id, len(user_messages_in_range),
            )

        extracted: list[Mapping[str, Any]] = []
        # `keep last _CONTEXT_WINDOW_MSGS`
        context_window: deque[dict[str, str]] = deque(maxlen=_CONTEXT_WINDOW_MSGS)

        for msg in memory_history:
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue

            content = (msg.get("content") or "").strip()

            if role == "assistant":
                context_window.append({"role": "assistant", "content": content})
                continue

            # role == "user" from here
            in_range = _in_processing_range(
                msg,
                after_turn_index=after_turn_index,
                through_turn_index=through_turn_index,
            )
            if not in_range or not content:
                # keep window updated
                if content:
                    context_window.append({"role": "user", "content": content})
                continue

            if _should_skip_memory_extraction(content):
                logger.info(
                    "session_finalizer: skipped low-signal KG extraction "
                    "(user=%s session=%s message_id=%s)",
                    user_id, session_id, _message_id(msg),
                )
                context_window.append({"role": "user", "content": content})
                continue

            prior = list(context_window)  # snapshot before the current message
            try:
                fact = await self.extractor(
                    message=content,
                    user_id=user_id,
                    session_id=session_id,
                    language=language,
                    preceding_context=prior or None,
                    session_metadata=session_metadata or None,
                    user_kg_context=user_kg_context or None,
                )
            except Exception as exc:
                logger.warning("kg extractor failed for one msg: %s", exc)
                context_window.append({"role": "user", "content": content})
                continue

            if fact:
                msg_id = _message_id(msg)
                if msg_id:
                    fact = dict(fact)
                    fact["__source_message_id"] = msg_id
                extracted.append(fact)

            context_window.append({"role": "user", "content": content})

        try:
            await self.kg_writer(
                user_id=user_id,
                session_id=session_id,
                summary=summary,
                extracted=extracted,
                language=language,
            )
        except Exception as exc:
            logger.exception("kg writer failed: %s", exc)
            return FinalizationResult(
                session_id=session_id,
                summary=summary,
                extracted_count=len(extracted),
                processed_count=len(process_history),
                through_turn_index=through_turn_index,
                error=f"kg_writer:{exc}",
            )

        return FinalizationResult(
            session_id=session_id,
            summary=summary,
            extracted_count=len(extracted),
            processed_count=len(process_history),
            through_turn_index=through_turn_index,
        )


def _turn_index(msg: Mapping[str, Any]) -> int | None:
    try:
        raw = msg.get("turn_index")
        if raw is None:
            return None
        return int(raw)
    except (TypeError, ValueError):
        return None


def _message_id(msg: Mapping[str, Any]) -> str | None:
    raw = msg.get("id")
    if raw is None:
        raw = msg.get("message_id")
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _in_processing_range(
    msg: Mapping[str, Any],
    *,
    after_turn_index: int | None,
    through_turn_index: int | None,
) -> bool:
    turn_index = _turn_index(msg)
    if turn_index is None:
        return True
    if after_turn_index is not None and turn_index <= after_turn_index:
        return False
    if through_turn_index is not None and turn_index > through_turn_index:
        return False
    return True


def _filter_phq9_messages(
    history: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    filtered: list[Mapping[str, Any]] = []
    previous_assistant_was_phq9 = False

    for msg in history:
        role = msg.get("role")
        is_phq9 = _is_phq9_message(
            msg,
            previous_assistant_was_phq9=previous_assistant_was_phq9,
        )

        if role == "assistant":
            previous_assistant_was_phq9 = is_phq9
        elif role == "user":
            # aply klo ngelang ngbaris
            previous_assistant_was_phq9 = False

        if is_phq9:
            logger.info(
                "session_finalizer: skipped PHQ-9 message for long-term memory "
                "(message_id=%s role=%s)",
                _message_id(msg), role,
            )
            continue

        filtered.append(msg)

    return filtered


def _format_transcript(history: Sequence[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    for msg in history:
        role = msg.get("role") or "other"
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        label = role.title() if isinstance(role, str) else "Other"
        parts.append(f"{label}: {content}")
    return "\n".join(parts)


__all__ = [
    "FinalizationResult",
    "SessionFinalizer",
    "HistoryLoader",
    "SessionMetadataLoaderFn",
    "UserContextLoaderFn",
    "SummarizerFn",
    "KGExtractorFn",
    "KGWriterFn",
]
