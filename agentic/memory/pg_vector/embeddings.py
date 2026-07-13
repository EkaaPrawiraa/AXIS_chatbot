"""wrap"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import struct
import urllib.error
import urllib.request
from typing import Iterable

logger = logging.getLogger(__name__)

EMBED_DIM: int = int(os.getenv("EMBED_DIM", "1536"))
EMBED_PROVIDER: str = (
    os.getenv("EMBED_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai"
).strip().lower()
EMBED_MODEL: str = os.getenv(
    "EMBED_MODEL",
    (
        "gemini-embedding-001"
        if EMBED_PROVIDER in {"gemini", "google"}
        else (
            "rjmalagon/gte-qwen2-1.5b-instruct-embed-f16"
            if EMBED_PROVIDER in {"local", "ollama"}
            else "text-embedding-3-small"
        )
    ),
)


# emb3-s

_openai_client = None
_gemini_client = None
_online_disabled: bool = False


def _try_get_openai_client():
    """lazy-load None if unavailable."""
    global _openai_client, _online_disabled
    if _online_disabled:
        return None
    if _openai_client is not None:
        return _openai_client
    if not os.getenv("OPENAI_API_KEY"):
        _online_disabled = True
        return None
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
        _openai_client = OpenAI()
        return _openai_client
    except ImportError:
        logger.warning(
            "openai not installed; falling back to deterministic stub "
            "embeddings. Install with: pip install openai"
        )
        _online_disabled = True
        return None


def _try_get_gemini_client():
    """load None lazy"""
    global _gemini_client, _online_disabled
    if _online_disabled:
        return None
    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        _online_disabled = True
        return None

    try:
        from google import genai  # type: ignore[import-not-found]

        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except ImportError:
        logger.warning(
            "google-genai not installed; falling back to deterministic stub "
            "embeddings. Install with: pip install google-genai"
        )
        _online_disabled = True
        return None


def _embed_online(text: str) -> list[float] | None:
    if EMBED_PROVIDER in {"gemini", "google", "google-genai", "google_genai"}:
        return _embed_gemini(text)
    if EMBED_PROVIDER in {"local", "ollama"}:
        return _embed_ollama(text)
    return _embed_openai(text)


def _embed_openai(text: str) -> list[float] | None:
    client = _try_get_openai_client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(input=text, model=EMBED_MODEL)
        return _fit_dimension(list(resp.data[0].embedding), source="openai")
    except Exception as exc:
        logger.warning(
            "OpenAI embed call failed (%s). Falling back to stub.", exc,
        )
        return None


def _embed_gemini(text: str) -> list[float] | None:
    client = _try_get_gemini_client()
    if client is None:
        return None
    try:
        from google.genai import types  # type: ignore[import-not-found]

        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM),
        )
        values = _extract_gemini_embedding_values(response)
        return _fit_dimension(values, source="gemini") if values else None
    except Exception as exc:
        logger.warning(
            "Gemini embed call failed (%s). Falling back to stub.", exc,
        )
        return None


def _embed_ollama(text: str) -> list[float] | None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")

    for path, payload in (
        ("/api/embed", {"model": EMBED_MODEL, "input": text}),
        ("/api/embeddings", {"model": EMBED_MODEL, "prompt": text}),
    ):
        try:
            req = urllib.request.Request(
                base_url + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            values = _extract_ollama_embedding_values(data)
            if values:
                return _fit_dimension(values, source="ollama")
        except urllib.error.HTTPError as exc:
            # fallback
            if path == "/api/embed" and exc.code == 404:
                continue
            logger.warning("Ollama embed call failed (%s). Falling back to stub.", exc)
            return None
        except Exception as exc:
            logger.warning("Ollama embed call failed (%s). Falling back to stub.", exc)
            return None

    return None


def _extract_ollama_embedding_values(response: object) -> list[float] | None:
    if not isinstance(response, dict):
        return None

    embedding = response.get("embedding")
    if isinstance(embedding, list):
        return [float(value) for value in embedding]

    embeddings = response.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list):
            return [float(value) for value in first]

    return None


def _extract_gemini_embedding_values(response: object) -> list[float] | None:
    embeddings = getattr(response, "embeddings", None)
    if embeddings:
        first = embeddings[0]
        values = getattr(first, "values", None)
        if values is not None:
            return list(values)
        if isinstance(first, dict):
            raw = first.get("values") or first.get("embedding")
            return list(raw) if raw is not None else None

    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = getattr(embedding, "values", None)
        if values is not None:
            return list(values)
        if isinstance(embedding, dict):
            raw = embedding.get("values") or embedding.get("embedding")
            return list(raw) if raw is not None else None

    if isinstance(response, dict):
        raw_embeddings = response.get("embeddings")
        if raw_embeddings:
            first = raw_embeddings[0]
            if isinstance(first, dict):
                raw = first.get("values") or first.get("embedding")
                return list(raw) if raw is not None else None
        raw_embedding = response.get("embedding")
        if isinstance(raw_embedding, dict):
            raw = raw_embedding.get("values") or raw_embedding.get("embedding")
            return list(raw) if raw is not None else None

    return None


def _fit_dimension(vector: list[float], *, source: str) -> list[float]:
    if len(vector) == EMBED_DIM:
        return vector
    logger.warning(
        "%s embedding returned %d dimensions; fitting to %d for pgvector schema",
        source,
        len(vector),
        EMBED_DIM,
    )
    if len(vector) > EMBED_DIM:
        return vector[:EMBED_DIM]
    return vector + [0.0] * (EMBED_DIM - len(vector))


# offline: stub

def _embed_offline(text: str) -> list[float]:
    """buat vector"""
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    raw: list[float] = []
    for i in range(EMBED_DIM):
        block = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()[:8]
        as_int = struct.unpack(">q", block)[0]
        raw.append(as_int / (2 ** 63))
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]



async def embed_text(text: str) -> list[float]:
    """[emb] * EMBED_DIM"""
    if not text or not text.strip():
        return [0.0] * EMBED_DIM

    online = await asyncio.to_thread(_embed_online, text)
    if online is not None:
        return online
    return _embed_offline(text)


async def embed_many(texts: Iterable[str]) -> list[list[float]]:
    """wrp batch embeds"""
    return [await embed_text(t) for t in texts]
