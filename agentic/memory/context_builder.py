"""Hybrid retrieval strategy."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from agentic.memory.pg_vector    import SearchHit, search_experience, search_memory
from agentic.memory.neo4j_client import get_client
from agentic.memory.knowledge_graph.kg_retriever import fetch_recurring_themes as _kg_fetch_themes
from agentic.memory.ranking import (
    Candidate,
    compute_relation_richness,
    rrf_fuse,
    graph_rerank,
    mmr_select,
)

logger = logging.getLogger(__name__)

SEMANTIC_TOP_K:        int   = 3
SEMANTIC_FLOOR:        float = 0.5    # cosine similarity floor for signal 2
SALIENCE_TOP_K:        int   = 3
SALIENCE_CUTOFF:       float = 0.5
EXPERIENCE_TOP_K:      int   = 3      # cosine top-k for past experiences (signal 4)
EXPERIENCE_FLOOR:      float = 0.5
SUBJECTS_TOP_K:          int   = 3    # signal 5: how many subjects to surface per turn
SUBJECTS_EXPERIENCE_CAP: int   = 3   # signal 5: experiences attached per subject

# backward compat aliases
PEOPLE_TOP_K          = SUBJECTS_TOP_K
PEOPLE_EXPERIENCE_CAP = SUBJECTS_EXPERIENCE_CAP

# Dynamic deepening (bounded graph expansion)
FOCUSED_TOP_K:         int   = 5
FOCUSED_FLOOR:         float = 0.4
FOCUSED_CHAR_BUDGET:   int   = 1600
FOCUSED_PEOPLE_CAP:    int   = 5
FOCUSED_TRIGGER_CAP:   int   = 5
FOCUSED_EMOTION_CAP:   int   = 5
FOCUSED_THOUGHT_CAP:   int   = 5
FOCUSED_BEHAVIOR_CAP:  int   = 5

# Benchmark retrieval mode (RM3: none / vector_only / full)
# none       : skip all retrieval, return empty context
# vector_only: run only pgvector signals (semantic_memory + semantic_experience)
# full       : full hybrid pipeline (default)
RETRIEVAL_MODE: str = os.getenv("RETRIEVAL_MODE", "full")

# Sensitivity tier retrieval policy (III.5.5)
# personal : full text, importance >= 0.5
# sensitive: description redacted, relations shown, importance >= 0.7, max 3
# trauma   : category-only (no descriptions), importance >= 0.8, max 2
SENSITIVITY_IMPORTANCE_PERSONAL  = 0.5
SENSITIVITY_IMPORTANCE_SENSITIVE = 0.7
SENSITIVITY_IMPORTANCE_TRAUMA    = 0.8
SENSITIVITY_MAX_SENSITIVE        = 3
SENSITIVITY_MAX_TRAUMA           = 2

_KEYWORD_STOPWORDS = {
    "aku", "gua", "gue", "saya", "kamu", "lu", "lo", "dan", "atau", "yang",
    "lagi", "jadi", "karena", "dengan", "untuk", "dari", "di", "ke", "itu",
    "ini", "apa", "gimana", "bagaimana", "bikin", "merasa", "ngerasa",
    "soal", "pernah", "cerita", "ceritakan", "takut",
    "the", "and", "that", "with", "from", "about",
}

_KEYWORD_SYNONYMS = {
    "temen": ["teman"],
    "teman": ["temen"],
    "ngomongin": ["membicarakan", "merendah", "direndahkan"],
    "sendirian": ["sendiri", "kesepian", "tidak punya siapa"],
    "bully": ["dibully", "dirundung"],
    "dibully": ["bully", "dirundung"],
    "gagal": ["failure", "mengecewakan"],
    "keluarga": ["family"],
}

_LOW_SPECIFICITY_RECALL_TERMS = {
    "cemas", "anxiety", "anxious", "sedih", "sad", "takut", "fear",
    "gagal", "failure", "buruk", "bad", "malu", "bersalah", "kesepian",
    "lelah", "capek", "fatigue", "tertekan", "stress", "stres",
    "mengecewakan",
}

_GENERIC_MEMORY_RE = re.compile(
    r"\b("
    r"ingat|ingetin|memori|memory|remember|recall|"
    r"tahu tentang aku|tau tentang aku|tentang aku"
    r")\b",
    re.IGNORECASE,
)

# Dynamic deepening (III.7.2): Tier 1 = back-reference, Tier 2 = clarification
_BACK_REFERENCE_RE = re.compile(
    r"\b("
    r"yang\s+(?:waktu|tadi|kemarin|dulu|sebelumnya|pernah)\s+(?:itu|kamu|lu|lo|aku|gue|gua|cerita)|"
    r"yang\s+kamu\s+(?:bilang|cerita|sebut|sebutin|mention)\s+(?:kemarin|tadi|sebelumnya|dulu|waktu\s+itu)|"
    r"yang\s+kita\s+(?:bicarain|omongin|bahas)\s+(?:kemarin|tadi|sebelumnya|dulu)|"
    r"waktu\s+(?:itu|kemarin|dulu)\s+(?:kamu|lu|lo|aku|gue|gua)|"
    r"sesi\s+(?:kemarin|sebelumnya|lalu|terakhir)|"
    r"kemarin\s+(?:kamu|lu|lo|aku|gue|gua|kata|bilang)|"
    r"kata\s+(?:kamu|lu|lo)\s+(?:kemarin|sebelumnya|waktu\s+itu)|"
    r"inget\s+(?:nggak|gak|ga|tidak)?\s*(?:waktu|pas|saat|ketika)|"
    r"that\s+time\s+(?:when|you|we)|"
    r"you\s+(?:said|mentioned|told\s+me)\s+(?:earlier|before|last\s+time|yesterday)"
    r")\b",
    re.IGNORECASE,
)

_CLARIFICATION_RE = re.compile(
    r"\b("
    r"jelasin|jelasin\s+lebih|jelaskan\s+(?:lebih|lagi)|"
    r"ceritain\s+(?:lebih|lagi)|ceritakan\s+(?:lebih|lagi)|"
    r"maksudnya\s+(?:apa|gimana|bagaimana)|"
    r"bisa\s+(?:jelasin|ceritain|elaborasi|explain)|"
    r"lebih\s+(?:detail|lengkap|dalam)|"
    r"explain\s+(?:that|more|further|in\s+detail)|"
    r"tell\s+me\s+more|elaborate|"
    r"gimana\s+ceritanya|"
    r"apa\s+(?:lagi|lebih)\s+(?:yang|tentang)|"
    r"tolong\s+(?:jelasin|ceritain|elaborasi)"
    r")\b",
    re.IGNORECASE,
)


def _is_back_reference(query_text: str | None) -> bool:
    """True when the user explicitly references something said in a prior session."""
    return bool(_BACK_REFERENCE_RE.search(query_text or ""))


def _is_clarification_request(query_text: str | None) -> bool:
    """True when the user asks for deeper elaboration on a previously-mentioned topic."""
    text = (query_text or "").strip()
    if not text or _is_generic_memory_query(text):
        return False
    if not _CLARIFICATION_RE.search(text):
        return False
    # Must have non-trivial content beyond just a clarification phrase
    terms = _query_terms(text)
    return len(terms) >= 1

_PHQ_MEMORY_NOISE_RE = re.compile(
    r"\b("
    r"phq[-\s]?9|tes\s+(?:mood|suasana hati)|kuesioner|"
    r"pertanyaan\s+\d+\s+(?:dari|/)\s*9|"
    r"dalam\s+2\s+minggu\s+terakhir|"
    r"skor\s+total|skor\s+phq|"
    r"sedikit\s+minat\s+atau\s+kesenangan|"
    r"merasa\s+buruk\s+tentang\s+diri\s+sendiri|"
    r"gagal\s+atau\s+mengecewakan\s+keluarga|"
    r"lebih\s+dari\s+setengah\s+hari|hampir\s+setiap\s+hari|"
    r"little\s+interest\s+or\s+pleasure|"
    r"feeling\s+bad\s+about\s+yourself|"
    r"failure\s+or\s+disappointing\s+(?:my|your)\s+family|"
    r"more\s+than\s+half\s+the\s+days|nearly\s+every\s+day"
    r")\b",
    re.IGNORECASE,
)


def _truncate(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    return text[: budget - 3].rstrip() + "..."


def _unwrap_json_text(value: str | None) -> str:
    """Extract plain text from legacy summaries stored as JSON blobs.

    Older sessions persisted `{"summary": "..."}` strings before the
    session_summarizer plain-prose rule existed. Retrieval must not leak
    that JSON into the LLM system prompt.
    """
    stripped = (value or "").strip()
    if not stripped.startswith("{"):
        return stripped
    try:
        import json as _json

        data = _json.loads(stripped)
        if isinstance(data, dict):
            for key in ("summary", "text", "content", "description", "result"):
                if isinstance(data.get(key), str) and data[key].strip():
                    return data[key].strip()
            for val in data.values():
                if isinstance(val, str) and len(val) > 10:
                    return val.strip()
    except Exception:
        pass
    return stripped


def _unwrap_all(items: list[str]) -> list[str]:
    return [_unwrap_json_text(s) for s in items if (s or "").strip()]


def _to_iso_string(val: Any) -> str | None:
    """Safely convert a Neo4j DateTime or any datetime-like value to ISO-8601."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _query_terms(query_text: str | None) -> list[str]:
    text = (query_text or "").lower()
    raw_terms = re.findall(r"[a-zA-Z0-9_\\-]+", text)
    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        term = term.strip("_-")
        if len(term) < 4 or term in _KEYWORD_STOPWORDS:
            continue
        for candidate in [term, *_KEYWORD_SYNONYMS.get(term, [])]:
            if candidate and candidate not in seen:
                seen.add(candidate)
                terms.append(candidate)
    return terms[:12]


def _is_generic_memory_query(query_text: str | None) -> bool:
    """True when the user asks broadly what AXIS remembers."""
    text = (query_text or "").strip().lower()
    if not text:
        return False
    if _GENERIC_MEMORY_RE.search(text):
        return True
    return False


def _contains_any_term(value: Any, terms: list[str]) -> bool:
    if not terms:
        return True
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_contains_any_term(v, terms) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_any_term(v, terms) for v in value)
    text = str(value).lower()
    return any(term in text for term in terms)


def _is_phq_memory_noise(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_is_phq_memory_noise(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_is_phq_memory_noise(v) for v in value)
    return bool(_PHQ_MEMORY_NOISE_RE.search(str(value).lower()))


def _without_phq_noise_strings(items: list[str]) -> list[str]:
    return [item for item in items if not _is_phq_memory_noise(item)]


def _without_phq_noise_dicts(
    items: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [
        item for item in items
        if not _is_phq_memory_noise([item.get(key) for key in keys])
    ]


def _filter_strings_by_terms(items: list[str], terms: list[str]) -> list[str]:
    if not terms:
        return items
    return [item for item in items if _contains_any_term(item, terms)]


def _filter_dicts_by_terms(
    items: list[dict[str, Any]],
    terms: list[str],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not terms:
        return items
    filtered: list[dict[str, Any]] = []
    for item in items:
        haystack = [item.get(key) for key in keys]
        if _contains_any_term(haystack, terms):
            filtered.append(item)
    return filtered


def _specific_anchor_terms(query_text: str | None) -> list[str]:
    """Terms that should anchor topic-specific recall, excluding affect words."""
    return [
        term for term in _query_terms(query_text)
        if term not in _LOW_SPECIFICITY_RECALL_TERMS
    ]


def _apply_sensitivity_redaction(
    rec: dict[str, Any],
    sensitivity_level: str,
    importance: float,
) -> dict[str, Any] | None:
    """
    Apply sensitivity tier policy (III.5.5) to a rehydrated node dict.

    - normal / public : pass through unchanged
    - personal        : full text only if importance >= 0.5; else None
    - sensitive       : redact description, keep relations, only if importance >= 0.7
    - trauma          : keep trigger categories only, no descriptions, only if importance >= 0.8
    Returns None when the node should be excluded entirely.
    """
    tier = (sensitivity_level or "normal").lower()
    if tier in ("normal", "public"):
        return rec
    if tier == "personal":
        if importance < SENSITIVITY_IMPORTANCE_PERSONAL:
            return None
        return rec  # full text at personal tier
    if tier == "sensitive":
        if importance < SENSITIVITY_IMPORTANCE_SENSITIVE:
            return None
        # Redact the main text, keep relational context only
        redacted = dict(rec)
        for text_key in ("description", "summary", "content"):
            if text_key in redacted:
                redacted[text_key] = "[Konten sensitif]"
        for exp_key in ("experiences",):
            if exp_key in redacted:
                redacted[exp_key] = []
        return redacted
    if tier == "trauma":
        if importance < SENSITIVITY_IMPORTANCE_TRAUMA:
            return None
        # Keep only trigger categories and emotion labels (no text content)
        redacted = dict(rec)
        for text_key in ("description", "summary", "content"):
            if text_key in redacted:
                redacted[text_key] = "[Konten trauma]"
        redacted["experiences"] = []
        redacted["thoughts"] = []
        redacted["subjects"] = []
        # Keep triggers (category only) and emotions (label only)
        redacted["behaviors"] = []
        return redacted
    return rec


async def _rehydrate_experience(user_id: str, exp_id: str) -> dict[str, Any] | None:
    """Return a bounded view of an Experience with sensitivity-tier policy applied."""
    records = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience {id: $exp_id})
        WHERE e.active = true
          AND coalesce(e.sensitivity_level, 'normal') IN ['normal', 'public', 'personal', 'sensitive', 'trauma']
        OPTIONAL MATCH (e)-[ip:INVOLVES_SUBJECT|INVOLVES_PERSON]->(p)
          WHERE (p:Subject OR p:Person)
            AND ip.t_invalid IS NULL
        OPTIONAL MATCH (e)-[rt:TRIGGERED_BY]->(t:Trigger)
          WHERE rt.t_invalid IS NULL AND coalesce(t.active, true) = true
        OPTIONAL MATCH (e)-[re:TRIGGERED_EMOTION]->(em:Emotion)
          WHERE re.t_invalid IS NULL AND coalesce(em.active, true) = true
                OPTIONAL MATCH (em)-[et:ACTIVATED_THOUGHT|ASSOCIATED_WITH]->(th:Thought)
                    WHERE et.t_invalid IS NULL
                        AND coalesce(th.active, true) = true
                        AND coalesce(th.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
                OPTIONAL MATCH (em)-[eb:LED_TO_BEHAVIOR]->(b1:Behavior)
                    WHERE eb.t_invalid IS NULL
                        AND coalesce(b1.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
                        AND coalesce(b1.active, true) = true
                OPTIONAL MATCH (th)-[tb:LED_TO_BEHAVIOR]->(b2:Behavior)
                    WHERE tb.t_invalid IS NULL
                        AND coalesce(b2.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
                        AND coalesce(b2.active, true) = true
        WITH e,
             collect(DISTINCT p.name) AS subjects,
             collect(DISTINCT t.description) AS triggers,
             collect(DISTINCT em.label) AS emotions,
             collect(DISTINCT {content: th.content, distortion: th.distortion}) AS thoughts,
             collect(DISTINCT {description: b1.description, category: b1.category, adaptive: b1.adaptive}) +
             collect(DISTINCT {description: b2.description, category: b2.category, adaptive: b2.adaptive}) AS behaviors
        RETURN e.description                                AS description,
               e.occurred_at                               AS occurred_at,
               e.valence                                   AS valence,
               e.significance                              AS significance,
               coalesce(e.sensitivity_level, 'normal')    AS sensitivity_level,
               [x IN subjects  WHERE x IS NOT NULL][..$people_cap]   AS subjects,
               [x IN triggers  WHERE x IS NOT NULL][..$trigger_cap]  AS triggers,
               [x IN emotions  WHERE x IS NOT NULL][..$emotion_cap]  AS emotions,
               [x IN thoughts  WHERE x.content IS NOT NULL][..$thought_cap]        AS thoughts,
               [x IN behaviors WHERE x.description IS NOT NULL][..$behavior_cap]   AS behaviors
        """,
        {
            "user_id":     user_id,
            "exp_id":      exp_id,
            "people_cap":  FOCUSED_PEOPLE_CAP,
            "trigger_cap": FOCUSED_TRIGGER_CAP,
            "emotion_cap": FOCUSED_EMOTION_CAP,
            "thought_cap": FOCUSED_THOUGHT_CAP,
            "behavior_cap": FOCUSED_BEHAVIOR_CAP,
        },
    )
    if not records:
        return None
    rec = dict(records[0])
    if _is_phq_memory_noise(rec.get("description")):
        return None
    tier = rec.get("sensitivity_level") or "normal"
    importance = float(rec.get("significance") or 0.0)
    return _apply_sensitivity_redaction(rec, tier, importance)


async def _rehydrate_memory(user_id: str, mem_id: str) -> dict[str, Any] | None:
    """Return a bounded view of a Memory with sensitivity-tier policy applied.

    Expands beyond the bare Memory summary to the experiences, emotions,
    thoughts, behaviours, triggers, and subjects captured in the SAME
    session (via the CONTAINS_MEMORY → Session anchor). Sensitivity tier
    policy (III.5.5) is applied post-fetch so redaction logic stays in Python
    rather than being duplicated across multiple Cypher branches.
    """
    records = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory {id: $mem_id})
        WHERE m.active = true
          AND coalesce(m.sensitivity_level, 'normal') IN ['normal', 'public', 'personal', 'sensitive', 'trauma']
        OPTIONAL MATCH (s:Session)-[:CONTAINS_MEMORY]->(m)
        OPTIONAL MATCH (s)-[:HAD_EXPERIENCE]->(e:Experience)
          WHERE e.active = true
            AND coalesce(e.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        OPTIONAL MATCH (e)-[ip:INVOLVES_SUBJECT|INVOLVES_PERSON]->(p)
          WHERE (p:Subject OR p:Person)
            AND ip.t_invalid IS NULL
        OPTIONAL MATCH (e)-[rt:TRIGGERED_BY]->(t:Trigger)
          WHERE rt.t_invalid IS NULL AND coalesce(t.active, true) = true
        OPTIONAL MATCH (e)-[re:TRIGGERED_EMOTION]->(em:Emotion)
          WHERE re.t_invalid IS NULL AND coalesce(em.active, true) = true
        OPTIONAL MATCH (em)-[et:ACTIVATED_THOUGHT|ASSOCIATED_WITH]->(th:Thought)
          WHERE et.t_invalid IS NULL
            AND coalesce(th.active, true) = true
            AND coalesce(th.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        OPTIONAL MATCH (em)-[eb:LED_TO_BEHAVIOR]->(b:Behavior)
          WHERE eb.t_invalid IS NULL
            AND coalesce(b.active, true) = true
            AND coalesce(b.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        WITH m, s,
             collect(DISTINCT e.description) AS exp_descriptions,
             collect(DISTINCT p.name)        AS subjects,
             collect(DISTINCT t.description) AS triggers,
             collect(DISTINCT em.label)      AS emotions,
             collect(DISTINCT {content: th.content, distortion: th.distortion}) AS thoughts,
             collect(DISTINCT {description: b.description, category: b.category, adaptive: b.adaptive}) AS behaviors
        RETURN m.summary                                    AS summary,
               m.importance                                 AS importance,
               m.created_at                                 AS created_at,
               coalesce(m.sensitivity_level, 'normal')     AS sensitivity_level,
               s.id                                         AS session_id,
               s.started_at                                 AS session_started_at,
               [x IN exp_descriptions WHERE x IS NOT NULL][..$exp_cap]      AS experiences,
               [x IN subjects         WHERE x IS NOT NULL][..$people_cap]  AS subjects,
               [x IN triggers         WHERE x IS NOT NULL][..$trigger_cap] AS triggers,
               [x IN emotions         WHERE x IS NOT NULL][..$emotion_cap] AS emotions,
               [x IN thoughts         WHERE x.content IS NOT NULL][..$thought_cap]        AS thoughts,
               [x IN behaviors        WHERE x.description IS NOT NULL][..$behavior_cap]   AS behaviors
        LIMIT 1
        """,
        {
            "user_id":      user_id,
            "mem_id":       mem_id,
            "exp_cap":      FOCUSED_PEOPLE_CAP,
            "people_cap":   FOCUSED_PEOPLE_CAP,
            "trigger_cap":  FOCUSED_TRIGGER_CAP,
            "emotion_cap":  FOCUSED_EMOTION_CAP,
            "thought_cap":  FOCUSED_THOUGHT_CAP,
            "behavior_cap": FOCUSED_BEHAVIOR_CAP,
        },
    )
    if not records:
        return None
    rec = dict(records[0])
    rec["summary"] = _unwrap_json_text(rec.get("summary"))
    if _is_phq_memory_noise(rec.get("summary")):
        return None
    rec["experiences"] = _without_phq_noise_strings(rec.get("experiences") or [])
    rec["thoughts"] = _without_phq_noise_dicts(rec.get("thoughts") or [], ("content",))
    tier = rec.get("sensitivity_level") or "normal"
    importance = float(rec.get("importance") or 0.0)
    return _apply_sensitivity_redaction(rec, tier, importance)


async def _fetch_keyword_experiences(
    user_id: str,
    query_text: str | None,
    *,
    limit: int = FOCUSED_TOP_K,
) -> list[dict[str, Any]]:
    """Fallback graph recall when embedding similarity does not anchor a hit.

    This keeps the knowledge graph useful even when embedding providers
    changed or old rows were embedded in a different vector space. It is
    intentionally bounded and only returns Experience ids whose own text
    or immediate relational ring matches query terms.
    """
    terms = _specific_anchor_terms(query_text) or _query_terms(query_text)
    if not terms:
        return []

    rows = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)
        WHERE coalesce(e.active, true) = true
          AND coalesce(e.sensitivity_level, 'normal') IN ['normal', 'public', 'personal', 'sensitive', 'trauma']
        OPTIONAL MATCH (e)-[rt:TRIGGERED_BY]->(tr:Trigger)
          WHERE rt.t_invalid IS NULL AND coalesce(tr.active, true) = true
        OPTIONAL MATCH (e)-[re:TRIGGERED_EMOTION]->(em:Emotion)
          WHERE re.t_invalid IS NULL AND coalesce(em.active, true) = true
        OPTIONAL MATCH (em)-[et:ACTIVATED_THOUGHT|ASSOCIATED_WITH]->(th:Thought)
          WHERE et.t_invalid IS NULL
            AND coalesce(th.active, true) = true
            AND coalesce(th.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        WITH e,
             toLower(coalesce(e.description, '')) AS exp_text,
             collect(DISTINCT toLower(coalesce(tr.description, ''))) AS trigger_texts,
             collect(DISTINCT toLower(coalesce(em.label, ''))) AS emotion_texts,
             collect(DISTINCT toLower(coalesce(th.content, ''))) AS thought_texts
        WITH e,
             reduce(score = 0, term IN $terms |
                score
                + CASE WHEN exp_text CONTAINS term THEN 3 ELSE 0 END
                + CASE WHEN any(x IN trigger_texts WHERE x CONTAINS term) THEN 2 ELSE 0 END
                + CASE WHEN any(x IN thought_texts WHERE x CONTAINS term) THEN 2 ELSE 0 END
                + CASE WHEN any(x IN emotion_texts WHERE x CONTAINS term) THEN 1 ELSE 0 END
             ) AS match_score
        WHERE match_score > 0
        RETURN e.id AS id, match_score, coalesce(e.significance, 0.0) AS significance
        ORDER BY match_score DESC, significance DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "terms": terms, "limit": limit},
    )

    hydrated: list[dict[str, Any]] = []
    for row in rows:
        rec = await _rehydrate_experience(user_id, str(row["id"]))
        if rec:
            rec["kind"] = "Experience"
            rec["similarity"] = None
            rec["keyword_score"] = row.get("match_score")
            hydrated.append(rec)
    return hydrated


def _format_focused_recall(items: list[dict[str, Any]], *, char_budget: int = FOCUSED_CHAR_BUDGET) -> str:
    if not items:
        return ""

    lines: list[str] = ["[Focused recall]"]
    seen_items: set[str] = set()
    for it in items:
        kind = it.get("kind", "unknown")
        identity = (
            f"{kind}|"
            f"{(it.get('description') or it.get('summary') or it.get('content') or '').strip().lower()}"
        )
        if identity in seen_items:
            continue
        seen_items.add(identity)
        sim = it.get("similarity")
        header_bits: list[str] = [str(kind)]
        if isinstance(sim, (int, float)):
            header_bits.append(f"similarity {sim:.2f}")
        header = " / ".join(header_bits)

        if kind == "Experience":
            desc = (it.get("description") or "").strip()
            if desc:
                lines.append(f"  - {header}: {desc}")
            else:
                lines.append(f"  - {header}")

            subjects = it.get("subjects") or []
            triggers = it.get("triggers") or []
            emotions = it.get("emotions") or []
            thoughts = it.get("thoughts") or []
            behaviors = it.get("behaviors") or []
            if subjects:
                lines.append("      * Subjects: " + ", ".join([p for p in subjects if p]))
            if triggers:
                lines.append("      * Triggers: " + ", ".join([t for t in triggers if t]))
            if emotions:
                lines.append("      * Emotions: " + ", ".join([e for e in emotions if e]))
            if thoughts:
                rendered_thoughts: list[str] = []
                for th in thoughts:
                    if not isinstance(th, dict):
                        continue
                    content = (th.get("content") or "").strip()
                    if not content:
                        continue
                    distortion = (th.get("distortion") or "").strip()
                    if distortion:
                        rendered_thoughts.append(f"{content} ({distortion})")
                    else:
                        rendered_thoughts.append(content)
                if rendered_thoughts:
                    lines.append("      * Thoughts: " + "; ".join(rendered_thoughts))

            if behaviors:
                rendered_behaviors: list[str] = []
                seen_behaviors: set[str] = set()
                for b in behaviors:
                    if not isinstance(b, dict):
                        continue
                    descb = (b.get("description") or "").strip()
                    if not descb:
                        continue
                    key = descb.lower()
                    if key in seen_behaviors:
                        continue
                    seen_behaviors.add(key)
                    cat = (b.get("category") or "").strip()
                    adaptive = b.get("adaptive")
                    parts: list[str] = []
                    if cat:
                        parts.append(cat)
                    parts.append(descb)
                    if adaptive is True:
                        parts.append("adaptive")
                    elif adaptive is False:
                        parts.append("maladaptive")
                    rendered_behaviors.append(" / ".join(parts))
                if rendered_behaviors:
                    lines.append("      * Behaviors: " + "; ".join(rendered_behaviors))

        elif kind == "Memory":
            summary = (it.get("summary") or "").strip()
            if summary:
                lines.append(f"  - {header}: {summary}")
            else:
                lines.append(f"  - {header}")
            # Session-neighbourhood expansion (see _rehydrate_memory) —
            # show only the bullets that have content so the prompt stays
            # tight on sparse memories.
            experiences = [e for e in (it.get("experiences") or []) if e]
            if experiences:
                lines.append("      * Experiences: " + "; ".join(experiences))
            subjects = [p for p in (it.get("subjects") or []) if p]
            if subjects:
                lines.append("      * Subjects: " + ", ".join(subjects))
            triggers = [t for t in (it.get("triggers") or []) if t]
            if triggers:
                lines.append("      * Triggers: " + ", ".join(triggers))
            emotions = [e for e in (it.get("emotions") or []) if e]
            if emotions:
                lines.append("      * Emotions: " + ", ".join(emotions))
            thoughts = it.get("thoughts") or []
            rendered_thoughts: list[str] = []
            for th in thoughts:
                if not isinstance(th, dict):
                    continue
                content = (th.get("content") or "").strip()
                if not content:
                    continue
                distortion = (th.get("distortion") or "").strip()
                rendered_thoughts.append(
                    f"{content} ({distortion})" if distortion else content
                )
            if rendered_thoughts:
                lines.append("      * Thoughts: " + "; ".join(rendered_thoughts))
            behaviors = it.get("behaviors") or []
            rendered_behaviors: list[str] = []
            seen_behaviors: set[str] = set()
            for b in behaviors:
                if not isinstance(b, dict):
                    continue
                descb = (b.get("description") or "").strip()
                if not descb:
                    continue
                category = (b.get("category") or "").strip()
                adaptive = b.get("adaptive")
                key = f"{category}|{descb}|{adaptive}"
                if key in seen_behaviors:
                    continue
                seen_behaviors.add(key)
                rendered_behaviors.append(descb)
            if rendered_behaviors:
                lines.append("      * Behaviors: " + "; ".join(rendered_behaviors))

        else:
            content = (it.get("content") or "").strip()
            if content:
                lines.append(f"  - {header}: {content}")
            else:
                lines.append(f"  - {header}")

    return _truncate("\n".join(lines), char_budget)



@dataclass
class RetrievedContext:
    recency_summaries:    list[str] = field(default_factory=list)
    semantic_memories:    list[str] = field(default_factory=list)
    salient_memories:     list[str] = field(default_factory=list)
    semantic_experiences: list[str] = field(default_factory=list)
    focused_recall:       str | None = None
    important_subjects:   list[dict[str, Any]] = field(default_factory=list)
    active_emotions:      list[dict[str, Any]] = field(default_factory=list)
    active_distortions:   list[dict[str, Any]] = field(default_factory=list)
    recurring_triggers:   list[dict[str, Any]] = field(default_factory=list)
    recurring_themes:     list[dict[str, Any]] = field(default_factory=list)
    # Structured retrieval context for audit / Phase-3 bucket access
    retrieval_context_dict: dict[str, Any] = field(default_factory=dict)

    def as_prompt_block(self) -> str:
        """
        Format the retrieved context as a structured text block for injection
        into the LLM system prompt. This is what memory_injection.md
        references as ``{kg_context}``.
        """
        lines: list[str] = ["=== Long-term memory context ==="]

        if self.recency_summaries:
            lines.append("\n[Recent sessions]")
            for i, s in enumerate(self.recency_summaries, 1):
                lines.append(f"  {i}. {s}")

        if self.semantic_memories:
            lines.append("\n[Relevant memories]")
            for s in self.semantic_memories:
                lines.append(f"  - {s}")

        if self.salient_memories:
            lines.append("\n[Significant memories]")
            for s in self.salient_memories:
                lines.append(f"  - {s}")

        if self.semantic_experiences:
            lines.append("\n[Past experiences]")
            for s in self.semantic_experiences:
                lines.append(f"  - {s}")

        if self.focused_recall:
            lines.append("\n" + self.focused_recall)

        if self.important_subjects:
            lines.append("\n[Important subjects]")
            for p in self.important_subjects:
                name        = p.get("name", "unknown")
                role        = p.get("role", "unknown")
                sentiment   = p.get("sentiment") or 0.0
                quality     = p.get("relationship_quality", "neutral")
                mentions    = p.get("mention_count", 0) or 0
                experiences = p.get("experiences") or []
                lines.append(
                    f"  - {name} ({role}, sentiment {sentiment:+.2f}, "
                    f"{quality}, mentioned {mentions}x)"
                )
                for exp in experiences:
                    lines.append(f"      * {exp}")

        if self.active_emotions:
            lines.append("\n[Recent emotional states]")
            for e in self.active_emotions:
                lines.append(
                    f"  - {e.get('label', 'unknown')} "
                    f"(intensity {e.get('intensity', 0):.1f}, "
                    f"valence {e.get('valence', 0):.2f})"
                )

        if self.active_distortions:
            lines.append("\n[Unchallenged cognitive distortions]")
            for t in self.active_distortions:
                if t.get("thought_type") == "core_belief":
                    label = "core belief"
                else:
                    label = t.get("distortion") or "unknown"
                lines.append(
                    f"  - [{label}] "
                    f"\"{t.get('content', '')}\" "
                    f"(believability {t.get('believability', 0):.1f})"
                )

        if self.recurring_triggers:
            lines.append("\n[Recurring triggers]")
            for t in self.recurring_triggers:
                lines.append(
                    f"  - [{t.get('category', 'unknown')}] "
                    f"{t.get('description', '')} "
                    f"(seen {t.get('frequency', 1)}x)"
                )

        if self.recurring_themes:
            lines.append("\n[Recurring themes across sessions]")
            for t in self.recurring_themes:
                name      = t.get("topic", "unknown")
                category  = t.get("category") or ""
                reinforced = t.get("times_reinforced") or 1
                sentiment  = t.get("avg_sentiment")
                parts: list[str] = [name]
                if category:
                    parts.append(category)
                parts.append(f"reinforced {reinforced}x")
                if sentiment is not None:
                    valence_label = "positive" if sentiment > 0.1 else ("negative" if sentiment < -0.1 else "neutral")
                    parts.append(f"valence {valence_label}")
                lines.append("  - " + ", ".join(parts))

        if len(lines) == 1:
            lines.append("  No prior context available for this user.")
        return "\n".join(lines)

    @property
    def important_people(self) -> list[dict[str, Any]]:
        """Backward-compat alias for ``important_subjects``."""
        return self.important_subjects

    @important_people.setter
    def important_people(self, value: list[dict[str, Any]]) -> None:
        self.important_subjects = value


# Signal 1: Recency

async def _fetch_recency(user_id: str) -> list[str]:
    """Always retrieve last 2 session summaries regardless of topic."""
    records = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAD_SESSION]->(s:Session)
        WHERE s.ended_at IS NOT NULL
          AND s.summary  IS NOT NULL
        MATCH (s)-[:CONTAINS_MEMORY]->(m:Memory)
        WHERE coalesce(m.active, true) = true
          AND coalesce(m.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        RETURN s.summary AS summary
        ORDER BY s.started_at DESC
        LIMIT 2
        """,
        {"user_id": user_id},
    )
    return _without_phq_noise_strings([r["summary"] for r in records])


# Signal 2: Semantic similarity (pgvector)

async def _touch_neo4j_access(node_ids: list[str]) -> None:
    """
    Bump ``last_accessed`` and ``access_count`` on the Neo4j Memory
    nodes that pgvector handed back. The Neo4j-side counters still
    drive the decay job; pgvector only tracks its own copy for retrieval.

    Failures here never propagate: a missed touch on access stats just
    delays decay, it does not corrupt retrieval.
    """
    if not node_ids:
        return
    try:
        await get_client().execute_write(
            """
            UNWIND $ids AS mid
            MATCH (m:Memory {id: mid})
            WHERE m.active = true
            SET m.last_accessed = datetime(),
                m.access_count  = coalesce(m.access_count, 0) + 1
            """,
            {"ids": node_ids},
        )
    except Exception as exc:
        logger.warning("Failed to refresh Memory access stats: %s", exc)


async def _fetch_semantic(
    user_id: str,
    query_embedding: list[float],
    *,
    prefetched_hits: list[SearchHit] | None = None,
) -> list[str]:
    """
    Top-K active Memory summaries by cosine similarity to the current
    message embedding, retrieved via pgvector. Refreshes the Neo4j-side
    access stats for the hits we return.

    ``prefetched_hits`` lets ``build_context`` share a single pgvector
    probe between this signal and the focused-recall pass so we don't
    hit Postgres twice per turn.
    """
    if prefetched_hits is None:
        hits: list[SearchHit] = await search_memory(
            user_id,
            query_embedding,
            top_k=SEMANTIC_TOP_K,
            min_similarity=SEMANTIC_FLOOR,
        )
    else:
        # Re-apply the stricter SEMANTIC_FLOOR/TOP_K on the shared list
        # so this signal stays semantically identical to the standalone
        # call. Sorting was already done by search_memory.
        hits = [h for h in prefetched_hits if h.similarity >= SEMANTIC_FLOOR][:SEMANTIC_TOP_K]
    if not hits:
        return []

    filtered_hits = [h for h in hits if not _is_phq_memory_noise(h.content)]
    await _touch_neo4j_access([h.neo4j_node_id for h in filtered_hits])
    return [h.content for h in filtered_hits]


# Signal 4: Past experiences (pgvector cosine on Experience nodes)

async def _touch_neo4j_experience_access(node_ids: list[str]) -> None:
    """
    Bump ``last_accessed`` and ``access_count`` on Experience nodes the
    pgvector probe surfaced. Same shape as the Memory touch helper, but
    against the :Experience label so the decay job can drop stale ones
    without affecting Memory counters. Failures never propagate.
    """
    if not node_ids:
        return
    try:
        await get_client().execute_write(
            """
            UNWIND $ids AS eid
            MATCH (e:Experience {id: eid})
            WHERE e.active = true
            SET e.last_accessed = datetime(),
                e.access_count  = coalesce(e.access_count, 0) + 1
            """,
            {"ids": node_ids},
        )
    except Exception as exc:
        logger.warning("Failed to refresh Experience access stats: %s", exc)


async def _fetch_semantic_experiences(
    user_id: str,
    query_embedding: list[float],
    *,
    prefetched_hits: list[SearchHit] | None = None,
) -> list[str]:
    """
    Top-K Experience descriptions by cosine similarity. This is the
    surface that fixes the "bot remembers the subject but not what they
    did" gap: Experience nodes were always written, just never read.

    Accepts ``prefetched_hits`` so the focused-recall pass can reuse the
    same pgvector probe (see :func:`build_context`).
    """
    if prefetched_hits is None:
        hits: list[SearchHit] = await search_experience(
            user_id,
            query_embedding,
            top_k=EXPERIENCE_TOP_K,
            min_similarity=EXPERIENCE_FLOOR,
        )
    else:
        hits = [h for h in prefetched_hits if h.similarity >= EXPERIENCE_FLOOR][:EXPERIENCE_TOP_K]
    if not hits:
        return []

    filtered_hits = [h for h in hits if not _is_phq_memory_noise(h.content)]
    await _touch_neo4j_experience_access(
        [h.neo4j_node_id for h in filtered_hits]
    )
    return [h.content for h in filtered_hits]


# Signal 5: Important subjects + their experiences (Neo4j graph traversal)

async def _fetch_subjects(user_id: str) -> list[dict[str, Any]]:
    """
    Top-K :Subject nodes (people, pets, objects, places, etc.) ranked by
    ``mention_count`` and absolute sentiment, each annotated with up to
    ``SUBJECTS_EXPERIENCE_CAP`` Experience descriptions reached through
    ``:INVOLVES_SUBJECT``.

    The traversal uses ``OPTIONAL MATCH`` so subjects with no recorded
    experience still surface (they will just render without bullet
    children). Both the relationship and the Experience are filtered
    on ``t_invalid IS NULL`` and ``active = true`` to honour soft
    deletion.
    """
    rows = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[r:HAS_SUBJECT|HAS_RELATIONSHIP_WITH]->(p)
        WHERE (p:Subject OR p:Person)
          AND r.t_invalid IS NULL
        OPTIONAL MATCH (p)<-[ip:INVOLVES_SUBJECT|INVOLVES_PERSON]-(e:Experience)
          WHERE e.active = true
            AND ip.t_invalid IS NULL
        WITH p, r,
             collect(DISTINCT e.description) AS all_experiences
        WITH p, r,
             [d IN all_experiences WHERE d IS NOT NULL][..$exp_cap] AS experiences
        RETURN p.name                  AS name,
               p.role                  AS role,
               p.sentiment             AS sentiment,
               coalesce(r.quality, 'unknown') AS relationship_quality,
               coalesce(p.mention_count, 0) AS mention_count,
               experiences
        ORDER BY coalesce(p.mention_count, 0) DESC,
                 abs(coalesce(p.sentiment, 0.0)) DESC
        LIMIT $top_k
        """,
        {
            "user_id": user_id,
            "top_k":   SUBJECTS_TOP_K,
            "exp_cap": SUBJECTS_EXPERIENCE_CAP,
        },
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["experiences"] = _without_phq_noise_strings(
            item.get("experiences") or []
        )
        out.append(item)
    return out


# backward compat alias
_fetch_people = _fetch_subjects


# Signal 3: Salience

async def _fetch_salient(user_id: str, emotion_label: str | None) -> list[str]:
    """
    Top-5 Memory nodes with importance > 0.5. ``emotion_label`` is
    accepted for API stability; the affective re-rank is applied later
    in the pipeline so this query stays a pure salience cut.
    """
    del emotion_label  # reserved for downstream affective re-ranker
    records = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
        WHERE m.active = true
          AND coalesce(m.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
          AND m.importance > $cutoff
        RETURN m.summary    AS summary,
               m.importance AS importance
        ORDER BY m.importance DESC
        LIMIT $top_k
        """,
        {
            "user_id": user_id,
            "cutoff":  SALIENCE_CUTOFF,
            "top_k":   SALIENCE_TOP_K,
        },
    )
    return _without_phq_noise_strings([r["summary"] for r in records])


# Supplementary KG reads (active emotions, distortions, triggers)

async def _fetch_active_emotions(user_id: str) -> list[dict[str, Any]]:
    """Recent active emotions from the last 7 days."""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)
        WHERE em.active = true
          AND coalesce(em.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
          AND em.timestamp > datetime() - duration('P7D')
        RETURN em.label     AS label,
               em.intensity AS intensity,
               em.valence   AS valence
        ORDER BY em.timestamp DESC
        LIMIT 5
        """,
        {"user_id": user_id},
    )


async def _fetch_active_distortions(user_id: str) -> list[dict[str, Any]]:
    """
    Unchallenged cognitive distortions plus core beliefs -- top 3.

    Core-belief thoughts (``thought_type == 'core_belief'``) are surfaced
    even without an attached distortion, since they are the most stable,
    identity-level thoughts a user holds and are otherwise invisible to
    every other retrieval signal. They are ranked ahead of ordinary
    (automatic/intermediate) distortions, then by recency within each tier.
    """
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(th:Thought)
        WHERE th.active = true
          AND th.challenged = false
          AND (th.distortion IS NOT NULL OR th.thought_type = 'core_belief')
          AND coalesce(th.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        RETURN th.content       AS content,
               th.distortion    AS distortion,
               th.believability AS believability,
               th.thought_type  AS thought_type
        ORDER BY CASE WHEN th.thought_type = 'core_belief' THEN 0 ELSE 1 END,
                 th.timestamp DESC
        LIMIT 3
        """,
        {"user_id": user_id},
    )


async def _fetch_recurring_triggers(user_id: str) -> list[dict[str, Any]]:
    """Top-3 most frequent active triggers."""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_TRIGGER]->(t:Trigger)
        WHERE t.active = true
          AND coalesce(t.sensitivity_level, 'normal') IN ['normal', 'public', 'personal']
        RETURN t.category    AS category,
               t.description AS description,
               t.frequency   AS frequency
        ORDER BY t.frequency DESC
        LIMIT 3
        """,
        {"user_id": user_id},
    )


async def _fetch_themes(user_id: str) -> list[dict[str, Any]]:
    """
    Top-5 recurring themes ranked by times_reinforced.

    Extends the base ``fetch_recurring_themes`` signal with ``category``
    and ``avg_sentiment`` so the prompt block can render richer labels.
    Topic nodes are not embeddable (no pgvector mirror), so this is a
    pure graph traversal — fast and always available.
    """
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[r:HAS_RECURRING_THEME]->(top:Topic)
        WHERE r.t_invalid IS NULL
        RETURN top.name          AS topic,
               top.category      AS category,
               top.avg_sentiment AS avg_sentiment,
               r.times_reinforced AS times_reinforced
        ORDER BY r.times_reinforced DESC, r.last_reinforced DESC
        LIMIT 5
        """,
        {"user_id": user_id},
    )



def _build_retrieval_context_dict(
    *,
    ctx: "RetrievedContext",
    ranked_candidates: list[Candidate],
    query_text: str | None,
    generic_memory_query: bool,
) -> dict[str, Any]:
    """Convert a RetrievedContext + ranked candidates into a structured dict.

    Bucket semantics (from design doc):
      focused_recall   — top candidates with causal KG chains; primary CBT context.
      recent_context   — most recent session summaries.
      semantic_context — semantic-only hits not covered by focused_recall.
      identity_context — stable identity signals: subjects, themes.
      safety_context   — crisis / safety-flagged candidates (empty on normal turns).
      assessment_context — PHQ-9 screening results (populated by assessment_repo).
      debug            — metadata about the ranking run for evaluation auditability.

    This structure enables:
    1. Evaluation auditability (which candidate scored how, why).
    2. Future Phase-3 where response_generator reads buckets instead of one string.
    3. Thesis Bab IV metrics: context_relevance@k, noise_rate, redundancy_rate.
    """
    focused: list[dict[str, Any]] = [c.to_dict() for c in ranked_candidates]

    # Focused recall ids to avoid duplicating in semantic_context.
    focused_ids: set[str] = {c.id for c in ranked_candidates}

    # recent_context: deduplicated recency summaries.
    recent: list[dict[str, Any]] = [
        {"text": s, "source": "recency"}
        for s in ctx.recency_summaries
        if s
    ]

    # semantic_context: semantic memories + experiences not already in focused.
    semantic_texts: set[str] = {c.get("text", "") for c in focused}
    semantic: list[dict[str, Any]] = []
    for s in ctx.semantic_memories:
        if s and s not in semantic_texts:
            semantic.append({"text": s, "source": "semantic_memory"})
            semantic_texts.add(s)
    for s in ctx.semantic_experiences:
        if s and s not in semantic_texts:
            semantic.append({"text": s, "source": "semantic_experience"})
            semantic_texts.add(s)
    for s in ctx.salient_memories:
        if s and s not in semantic_texts:
            semantic.append({"text": s, "source": "salient"})
            semantic_texts.add(s)

    identity: dict[str, Any] = {
        "subjects": ctx.important_subjects,
        "themes": ctx.recurring_themes,
        "emotions": ctx.active_emotions,
        "distortions": ctx.active_distortions,
        "triggers": ctx.recurring_triggers,
    }

    from agentic.memory.ranking.rrf import RRF_K
    from agentic.memory.ranking.reranker import MMR_LAMBDA, _W_RRF, _W_IMP, _W_RICH, _W_REC, _W_SAFE

    return {
        "focused_recall": focused,
        "recent_context": recent,
        "semantic_context": semantic,
        "identity_context": identity,
        "safety_context": [],
        "assessment_context": [],
        "debug": {
            "query_text": query_text or "",
            "generic_memory_query": generic_memory_query,
            "ranking_strategy": "rrf_graph_rerank_mmr_v1",
            "candidates_after_mmr": len(focused),
            "rrf_k": RRF_K,
            "mmr_lambda": MMR_LAMBDA,
            "graph_reranker_weights": {
                "rrf": _W_RRF,
                "importance": _W_IMP,
                "relation_richness": _W_RICH,
                "recency": _W_REC,
                "safety": _W_SAFE,
            },
        },
    }



async def build_context(
    user_id: str,
    query_embedding: list[float] | None = None,
    current_emotion_label: str | None = None,
    query_text: str | None = None,
) -> RetrievedContext:
    """
    Run every retrieval signal in parallel and assemble RetrievedContext.

    Args:
        user_id: The user whose context to retrieve.
        query_embedding: Embedding of the current user message. If None,
                         signals 2 and 4 (semantic Memory and Experience)
                         are skipped because both rely on cosine similarity.
                         When present, focused recall (bounded subgraph
                         expansion) also fires unconditionally.
        current_emotion_label: Detected emotion label for salience boost.
        query_text: Used for dynamic deepening detection (back-reference and
                    clarification triggers per III.7.2) and query-aware gating.

    Returns:
        RetrievedContext with all signals populated. Call .as_prompt_block()
        to get the formatted string for LLM injection.
    """
    # Dynamic deepening (III.7.2): expand subgraph when back-reference or
    # clarification is detected. Conservative gate: only fires when query
    # has non-trivial content, never on generic memory queries.
    deepening_back_ref    = _is_back_reference(query_text)
    deepening_clarif      = _is_clarification_request(query_text)
    dynamic_deepening     = deepening_back_ref or deepening_clarif
    effective_focused_top_k     = (FOCUSED_TOP_K * 2) if dynamic_deepening else FOCUSED_TOP_K
    effective_focused_budget    = (FOCUSED_CHAR_BUDGET * 2) if dynamic_deepening else FOCUSED_CHAR_BUDGET

    if dynamic_deepening:
        logger.debug(
            "Dynamic deepening triggered for user=%s back_ref=%s clarif=%s",
            user_id, deepening_back_ref, deepening_clarif,
        )

    # Retrieval mode gate (benchmark RM3)
    _mode = RETRIEVAL_MODE.lower()
    if _mode == "none":
        logger.debug("RETRIEVAL_MODE=none: returning empty context for user=%s", user_id)
        return RetrievedContext()

    if _mode == "vector_only":
        logger.debug("RETRIEVAL_MODE=vector_only: pgvector-only path for user=%s", user_id)
        _sem_mem: list[dict[str, Any]] = []
        _sem_exp: list[dict[str, Any]] = []
        if query_embedding:
            try:
                _mem_hits, _exp_hits = await asyncio.gather(
                    search_memory(
                        user_id, query_embedding,
                        top_k=SEMANTIC_TOP_K, min_similarity=SEMANTIC_FLOOR,
                    ),
                    search_experience(
                        user_id, query_embedding,
                        top_k=EXPERIENCE_TOP_K, min_similarity=EXPERIENCE_FLOOR,
                    ),
                )
                _sem_mem = [{"summary": h.text, "source": "semantic_memory"} for h in _mem_hits]
                _sem_exp = [{"description": h.text, "source": "semantic_experience"} for h in _exp_hits]
            except Exception as exc:
                logger.warning("vector_only pgvector fetch failed: %s", exc)
        return RetrievedContext(
            semantic_memories=_sem_mem,
            semantic_experiences=_sem_exp,
        )

    # Single pgvector probe per kind. We fetch enough to satisfy BOTH
    # the standalone semantic signals (TOP_K=3, floor 0.5) AND the
    # focused-recall pass (TOP_K=2, floor 0.4) in one round trip. Each
    # downstream consumer re-applies its own floor + top-k.
    pooled_top_k = max(SEMANTIC_TOP_K, effective_focused_top_k) + 2
    pooled_floor = min(SEMANTIC_FLOOR, FOCUSED_FLOOR)
    pooled_mem_hits: list[SearchHit] = []
    pooled_exp_hits: list[SearchHit] = []
    if query_embedding:
        try:
            pooled_mem_hits, pooled_exp_hits = await asyncio.gather(
                search_memory(
                    user_id, query_embedding,
                    top_k=pooled_top_k, min_similarity=pooled_floor,
                ),
                search_experience(
                    user_id, query_embedding,
                    top_k=pooled_top_k, min_similarity=pooled_floor,
                ),
            )
        except Exception as exc:
            logger.warning("pgvector pooled fetch failed: %s", exc)

    async def _empty_list() -> list:
        return []
    semantic_memory_task = (
        _fetch_semantic(user_id, query_embedding, prefetched_hits=pooled_mem_hits)
        if query_embedding
        else _empty_list()
    )
    semantic_experience_task = (
        _fetch_semantic_experiences(user_id, query_embedding, prefetched_hits=pooled_exp_hits)
        if query_embedding
        else _empty_list()
    )

    results = await asyncio.gather(
        _fetch_recency(user_id),                          # 0 — static
        semantic_memory_task,                             # 1 — dynamic
        _fetch_salient(user_id, current_emotion_label),  # 2 — static
        semantic_experience_task,                         # 3 — dynamic
        _fetch_subjects(user_id),                          # 4 — static
        _fetch_active_emotions(user_id),                  # 5 — static
        _fetch_active_distortions(user_id),               # 6 — static
        _fetch_recurring_triggers(user_id),               # 7 — static
        _fetch_themes(user_id),                           # 8 — static (themes)
        return_exceptions=True,
    )

    def safe(result: Any, default: list) -> list:
        if isinstance(result, Exception):
            logger.warning("Context retrieval signal failed: %s", result)
            return default
        return result

    ctx = RetrievedContext(
        recency_summaries=safe(results[0], []),
        semantic_memories=safe(results[1], []),
        salient_memories=safe(results[2], []),
        semantic_experiences=safe(results[3], []),
        important_subjects=safe(results[4], []),
        active_emotions=safe(results[5], []),
        active_distortions=safe(results[6], []),
        recurring_triggers=safe(results[7], []),
        recurring_themes=safe(results[8], []),
    )
    query_terms = _query_terms(query_text)
    generic_memory_query = _is_generic_memory_query(query_text)

    # Focused recall — bounded subgraph expansion with RRF + graph reranker + MMR.
    #
    # Pipeline:
    #   1. RRF fuses semantic-memory and semantic-experience ranked lists so
    #      a candidate appearing in both signals rises above single-signal hits.
    #      (Cormack, Clarke & Buettcher, 2009)
    #   2. Graph reranker boosts candidates via importance, KG relation richness,
    #      and recency after rehydration delivers the full neighbourhood.
    #      (design doc: kg_context_structuring_and_ranking_strategy.md)
    #   3. MMR deduplicates the reranked pool so no two selected candidates
    #      convey the same information. (Carbonell & Goldstein, 1998)
    #
    # These sets feed the selective overlap removal further down.
    focused_memory_summaries: set[str] = set()
    focused_experience_descriptions: set[str] = set()
    _ranked_candidates: list[Candidate] = []   # for retrieval_context_dict

    if query_embedding:
        try:
            mem_hits = [h for h in pooled_mem_hits if h.similarity >= FOCUSED_FLOOR]
            exp_hits = [h for h in pooled_exp_hits if h.similarity >= FOCUSED_FLOOR]

            # Stage 1: RRF fusion
            # Each signal provides a ranked list of node ids (best → first).
            mem_ranked = [h.neo4j_node_id for h in mem_hits]
            exp_ranked = [h.neo4j_node_id for h in exp_hits]
            rrf_scores = rrf_fuse([mem_ranked, exp_ranked])

            # Build a lookup so we can retrieve SearchHit metadata per node id.
            hit_lookup: dict[str, tuple[str, SearchHit]] = {}
            for h in mem_hits:
                hit_lookup.setdefault(h.neo4j_node_id, ("Memory", h))
            for h in exp_hits:
                if h.neo4j_node_id not in hit_lookup:
                    hit_lookup[h.neo4j_node_id] = ("Experience", h)

            # Order by RRF score, deduplicate, and cap at FOCUSED_TOP_K.
            picked_ids: list[str] = []
            seen_ids: set[str] = set()
            for nid in sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True):
                if nid in seen_ids or nid not in hit_lookup:
                    continue
                seen_ids.add(nid)
                picked_ids.append(nid)
                if len(picked_ids) >= effective_focused_top_k:
                    break

            # Stage 2: Rehydrate and build Candidates
            hydrated: list[dict[str, Any]] = []
            ranking_candidates: list[Candidate] = []

            for nid in picked_ids:
                kind, h = hit_lookup[nid]
                if kind == "Experience":
                    rec = await _rehydrate_experience(user_id, nid)
                    if rec:
                        rec["kind"] = "Experience"
                        rec["neo4j_node_id"] = nid
                        rec["similarity"] = h.similarity
                        hydrated.append(rec)
                        ranking_candidates.append(Candidate(
                            id=nid,
                            type="Experience",
                            text=rec.get("description") or "",
                            source_signal="semantic_experience",
                            similarity=h.similarity,
                            importance=float(rec.get("significance") or 0.0),
                            created_at_iso=_to_iso_string(rec.get("occurred_at")),
                            relation_richness=compute_relation_richness(rec),
                            hydrated=rec,
                        ))
                elif kind == "Memory":
                    rec = await _rehydrate_memory(user_id, nid)
                    if rec:
                        rec["kind"] = "Memory"
                        rec["neo4j_node_id"] = nid
                        rec["similarity"] = h.similarity
                        hydrated.append(rec)
                        ranking_candidates.append(Candidate(
                            id=nid,
                            type="Memory",
                            text=rec.get("summary") or "",
                            source_signal="semantic_memory",
                            similarity=h.similarity,
                            importance=float(rec.get("importance") or 0.0),
                            created_at_iso=_to_iso_string(rec.get("created_at")),
                            relation_richness=compute_relation_richness(rec),
                            hydrated=rec,
                        ))

            # Stage 3: Graph reranker
            if ranking_candidates:
                ranking_candidates = graph_rerank(ranking_candidates, rrf_scores)

                # Stage 4: MMR deduplication
                final_selected = mmr_select(
                    ranking_candidates, top_n=effective_focused_top_k
                )
                _ranked_candidates = final_selected

                # Re-order hydrated to match MMR selection (best first).
                selected_id_set = {c.id for c in final_selected}
                id_to_hydrated: dict[str, dict[str, Any]] = {
                    h.get("neo4j_node_id", ""): h for h in hydrated
                }
                hydrated = [
                    id_to_hydrated[c.id]
                    for c in final_selected
                    if c.id in id_to_hydrated
                ]

            anchor_terms = _specific_anchor_terms(query_text)
            if anchor_terms and not generic_memory_query:
                hydrated = [
                    item for item in hydrated
                    if _contains_any_term(item, anchor_terms)
                ]

            if hydrated:
                ctx.focused_recall = _format_focused_recall(hydrated, char_budget=effective_focused_budget)
                for h in hydrated:
                    kind = h.get("kind")
                    if kind == "Memory":
                        s = (h.get("summary") or "").strip()
                        if s:
                            focused_memory_summaries.add(s)
                        for exp_desc in (h.get("experiences") or []):
                            if exp_desc:
                                focused_experience_descriptions.add(
                                    str(exp_desc).strip()
                                )
                    elif kind == "Experience":
                        d = (h.get("description") or "").strip()
                        if d:
                            focused_experience_descriptions.add(d)

            if not hydrated and query_text:
                hydrated = await _fetch_keyword_experiences(user_id, query_text)
                if hydrated:
                    ctx.focused_recall = _format_focused_recall(hydrated, char_budget=effective_focused_budget)
                    # Keyword fallback candidates still go through the
                    # graph reranker (no RRF, but importance + richness boost)
                    # so they appear in retrieval_context_dict.focused_recall.
                    kb_candidates: list[Candidate] = []
                    for h in hydrated:
                        d = (h.get("description") or "").strip()
                        if d:
                            focused_experience_descriptions.add(d)
                        nid = h.get("neo4j_node_id") or d[:32]
                        kb_candidates.append(Candidate(
                            id=nid,
                            type="Experience",
                            text=d,
                            source_signal="keyword_graph",
                            similarity=0.0,
                            importance=float(h.get("significance") or 0.0),
                            created_at_iso=_to_iso_string(h.get("occurred_at")),
                            relation_richness=compute_relation_richness(h),
                            hydrated=h,
                        ))
                    if kb_candidates:
                        # keyword_score acts as proxy for RRF; normalise 0-1
                        max_ks = max((h.get("keyword_score") or 1) for h in hydrated)
                        kb_rrf = {
                            c.id: (h.get("keyword_score") or 0) / max(max_ks, 1)
                            for c, h in zip(kb_candidates, hydrated)
                        }
                        _ranked_candidates = graph_rerank(kb_candidates, kb_rrf)
        except Exception as exc:
            logger.warning("Focused recall deepening failed: %s", exc)

    ctx.recency_summaries = _without_phq_noise_strings(_unwrap_all(ctx.recency_summaries))
    ctx.semantic_memories = _without_phq_noise_strings(_unwrap_all(ctx.semantic_memories))
    ctx.salient_memories = _without_phq_noise_strings(_unwrap_all(ctx.salient_memories))
    ctx.semantic_experiences = _without_phq_noise_strings(_unwrap_all(ctx.semantic_experiences))
    ctx.important_subjects = _without_phq_noise_dicts(
        ctx.important_subjects,
        ("name", "role", "relationship_quality", "experiences"),
    )
    ctx.active_distortions = _without_phq_noise_dicts(
        ctx.active_distortions,
        ("content", "distortion"),
    )
    ctx.recurring_triggers = _without_phq_noise_dicts(
        ctx.recurring_triggers,
        ("category", "description"),
    )
    ctx.recurring_themes = _without_phq_noise_dicts(
        ctx.recurring_themes,
        ("topic", "category"),
    )

    # Query-aware gating for static graph signals. Recency, salience,
    # subjects, emotions, distortions, triggers, and themes are useful
    # identity/background signals, but they should not flood every
    # specific turn. A broad "what do you remember about me?" query keeps
    # the full profile-like view; otherwise static signals must overlap
    # with the user's current retrieval terms.
    if query_terms and not generic_memory_query:
        ctx.recency_summaries = _filter_strings_by_terms(
            ctx.recency_summaries, query_terms
        )
        ctx.salient_memories = _filter_strings_by_terms(
            ctx.salient_memories, query_terms
        )
        ctx.important_subjects = _filter_dicts_by_terms(
            ctx.important_subjects,
            query_terms,
            ("name", "role", "relationship_quality", "experiences"),
        )
        ctx.active_emotions = _filter_dicts_by_terms(
            ctx.active_emotions, query_terms, ("label",)
        )
        ctx.active_distortions = _filter_dicts_by_terms(
            ctx.active_distortions, query_terms, ("content", "distortion")
        )
        ctx.recurring_triggers = _filter_dicts_by_terms(
            ctx.recurring_triggers, query_terms, ("category", "description")
        )
        ctx.recurring_themes = _filter_dicts_by_terms(
            ctx.recurring_themes, query_terms, ("topic", "category")
        )

    # Selective overlap removal — skip Memory summaries and Experience
    # descriptions that already appear in the [Focused recall] section
    # to avoid the same fact repeating across 3-4 sections of the prompt.
    # Identity-layer signals (themes, people, distortions, triggers,
    # emotions) are NOT filtered here: they're orthogonal to focused
    # recall and carry information that subgraph expansion never covers.
    if focused_memory_summaries:
        ctx.recency_summaries = [
            s for s in ctx.recency_summaries
            if (s or "").strip() not in focused_memory_summaries
        ]
        ctx.semantic_memories = [
            s for s in ctx.semantic_memories
            if (s or "").strip() not in focused_memory_summaries
        ]
        ctx.salient_memories = [
            s for s in ctx.salient_memories
            if (s or "").strip() not in focused_memory_summaries
        ]
    if focused_experience_descriptions:
        ctx.semantic_experiences = [
            s for s in ctx.semantic_experiences
            if (s or "").strip() not in focused_experience_descriptions
        ]

    # Cross-section dedup among the surviving Memory-pool signals so a
    # single summary doesn't surface in both recency AND semantic AND
    # salient. Side-effect trick: ``not seen.add(s)`` always evaluates
    # True (set.add returns None), so it both filters and accumulates.
    seen: set[str] = set(ctx.recency_summaries)
    ctx.semantic_memories = [
        s for s in ctx.semantic_memories if s not in seen and not seen.add(s)  # type: ignore[func-returns-value]
    ]
    ctx.salient_memories = [
        s for s in ctx.salient_memories  if s not in seen and not seen.add(s)  # type: ignore[func-returns-value]
    ]


    # Build structured retrieval_context_dict for Phase-1/2 auditability.
    # This does NOT change what the response generator receives (kg_context
    # string stays identical); it only adds a structured parallel view of
    # the same data for evaluation tooling and future Phase-3 bucket access.
    ctx.retrieval_context_dict = _build_retrieval_context_dict(
        ctx=ctx,
        ranked_candidates=_ranked_candidates,
        query_text=query_text,
        generic_memory_query=generic_memory_query,
    )

    logger.debug(
        "Context built for %s: recency=%d semantic=%d salient=%d "
        "experiences=%d people=%d themes=%d focused_recall=%s "
        "ranked_candidates=%d",
        user_id,
        len(ctx.recency_summaries),
        len(ctx.semantic_memories),
        len(ctx.salient_memories),
        len(ctx.semantic_experiences),
        len(ctx.important_subjects),
        len(ctx.recurring_themes),
        "yes" if ctx.focused_recall else "no",
        len(_ranked_candidates),
    )
    return ctx
