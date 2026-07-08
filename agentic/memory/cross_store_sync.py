"""orchestrate mem backends"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from agentic.memory.neo4j_client import get_client

# side: Neo4j.
from agentic.memory.knowledge_graph.kg_modifier import mark_embedding_synced
from agentic.memory.knowledge_graph.kg_deleter import (
    invalidate_message as _kg_invalidate_message,
    purge_message      as _kg_purge_message,
    purge_session      as _kg_purge_session,
    purge_user         as _kg_purge_user,
    purge_user_memory  as _kg_purge_user_memory,
)

# pgvector side (Postgres mirrors structure for ANN search)
from agentic.memory.pg_vector import (
    SearchHit,
    embed_text,
    upsert_memory,
    upsert_experience,
    upsert_thought,
    upsert_trigger,
    upsert_behavior,
    search_memory,
    search_experience,
    search_thought,
    search_trigger,
    search_behavior,
    archive_node    as _pg_archive_node,
    purge_node      as _pg_purge_node,
    purge_user      as _pg_purge_user,
)

logger = logging.getLogger(__name__)


# dedup v1.1 2 1.3 1.4

MERGE_THRESHOLD:  float = 0.85
REVIEW_THRESHOLD: float = 0.65


# `per-label config: read unsynced rows, upsert, searcher`

_LABEL_CONFIG: dict[str, dict[str, Any]] = {
    "Memory": {
        "content_field":      "summary",
        "importance_field":   "importance",
        "importance_default": 0.5,
        "anchor_edge":        "HAS_MEMORY",
        "upsert":             upsert_memory,
        "search":             search_memory,
    },
    "Experience": {
        "content_field":      "description",
        "importance_field":   "significance",
        "importance_default": 0.5,
        "anchor_edge":        "EXPERIENCED",
        "upsert":             upsert_experience,
        "search":             search_experience,
    },
    "Thought": {
        "content_field":      "content",
        "importance_field":   "believability",
        "importance_default": 0.5,
        "anchor_edge":        "HAS_THOUGHT",
        "upsert":             upsert_thought,
        "search":             search_thought,
    },
    "Trigger": {
        "content_field":      "description",
        "importance_field":   None,           # not on the node; use default
        "importance_default": 0.5,
        "anchor_edge":        "HAS_TRIGGER",
        "upsert":             upsert_trigger,
        "search":             search_trigger,
    },
    "Behavior": {
        "content_field":      "description",
        "importance_field":   "confidence",
        "importance_default": 0.5,
        "anchor_edge":        "EXHIBITED",   # behavior_kg.py uses EXHIBITED, not HAS_BEHAVIOR
        "upsert":             upsert_behavior,
        "search":             search_behavior,
    },
}


def _upserter_for(label: str):
    return _LABEL_CONFIG[label]["upsert"]


# mirror node into pgvector

async def sync_embedding_to_pgvector(
    *,
    label: str,
    node_id: str,
    user_id: str,
    content: str,
    embedding: list[float] | None,
    importance: float = 0.5,
) -> bool:
    """mirror_node_to_pgvector() sync_embedding() return sync_status() handle_errors()"""
    if label not in _LABEL_CONFIG:
        raise ValueError(f"label {label!r} is not embeddable")

    if embedding is None:
        # `no vec; node stays sync=false`
        return False

    upsert = _upserter_for(label)
    ok = await upsert(
        user_id=user_id,
        neo4j_node_id=node_id,
        content=content,
        embedding=embedding,
        importance=importance,
    )
    if not ok:
        return False

    try:
        await mark_embedding_synced(label, node_id, synced=True)
        return True
    except Exception as exc:
        logger.warning(
            "Failed to flip embedding_synced on %s/%s: %s. "
            "Retry sweep will reconcile.",
            label, node_id, exc,
        )
        return False


# cosine_dedup_probe

async def find_similar_node(
    *,
    label: str,
    embedding: list[float] | None,
    user_id: str,
    min_similarity: float = REVIEW_THRESHOLD,
) -> dict[str, Any] | None:
    """return closest_active_node(embedding, min_similarity)"""
    if embedding is None:
        return None

    cfg = _LABEL_CONFIG.get(label)
    if cfg is None:
        return None

    searcher = cfg["search"]
    hits: list[SearchHit] = await searcher(
        user_id, embedding, top_k=1, min_similarity=min_similarity,
    )
    if not hits:
        return None

    top = hits[0]
    return {
        "id":          top.neo4j_node_id,
        "description": top.content,
        "similarity":  top.similarity,
    }


# sdbr

async def invalidate_message_full(
    message_id: str,
    *,
    reason: str = "user_deleted_message",
) -> dict[str, int]:
    """archive_embedded_rows()"""
    kg_report = await _kg_invalidate_message(message_id, reason=reason)

    archived = 0
    for row in kg_report.get("deactivated_rows", []):
        label   = row.get("label")
        node_id = row.get("id")
        if not label or not node_id or label not in _LABEL_CONFIG:
            continue
        archived += await _pg_archive_node(label, node_id)

    return {
        "edges_touched":     kg_report.get("edges_touched", 0),
        "nodes_deactivated": kg_report.get("nodes_deactivated", 0),
        "pgvector_archived": archived,
    }


# hard delete 3

async def purge_message_full(message_id: str) -> dict[str, int]:
    """purge embeddables"""
    kg_report = await _kg_purge_message(message_id)

    purged = 0
    for row in kg_report.get("deleted_rows", []):
        label   = row.get("label")
        node_id = row.get("id")
        if not label or not node_id or label not in _LABEL_CONFIG:
            continue
        purged += await _pg_purge_node(label, node_id)

    return {
        "edges_with_pruned_provenance":
            kg_report.get("edges_with_pruned_provenance", 0),
        "nodes_deleted":         kg_report.get("nodes_deleted", 0),
        "pgvector_rows_deleted": purged,
    }


async def purge_session_full(
    session_id: str,
    *,
    message_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """purge msg provenance, remove session-scoped facts, mirror nodes to pgvector."""
    message_reports = []
    for message_id in message_ids or []:
        if not message_id:
            continue
        message_reports.append(await purge_message_full(message_id))

    kg_report = await _kg_purge_session(session_id)
    purged = 0
    for row in kg_report.get("deleted_rows", []):
        label = row.get("label")
        node_id = row.get("id")
        if not label or not node_id or label not in _LABEL_CONFIG:
            continue
        purged += await _pg_purge_node(label, node_id)

    return {
        "message_reports": message_reports,
        "relationships_deleted": kg_report.get("relationships_deleted", 0),
        "sessions_deleted": kg_report.get("sessions_deleted", 0),
        "nodes_deleted": kg_report.get("nodes_deleted", 0),
        "pgvector_rows_deleted": purged + sum(
            int(report.get("pgvector_rows_deleted", 0)) for report in message_reports
        ),
    }


async def purge_user_memory_full(user_id: str) -> dict[str, Any]:
    """`drop mem & pgvec`"""
    kg_report = await _kg_purge_user_memory(user_id)
    pg_deleted = await _pg_purge_user(user_id)
    return {
        "nodes_deleted": kg_report.get("nodes_deleted", 0),
        "sessions_deleted": kg_report.get("sessions_deleted", 0),
        "user_relationships_deleted": kg_report.get("user_relationships_deleted", 0),
        "user_deleted": 0,
        "pgvector_rows_deleted": sum(pg_deleted.values()),
        "pgvector_per_label": pg_deleted,
    }


async def purge_user_full(user_id: str) -> dict[str, Any]:
    """``purge_user`` & drop pgvector rows"""
    kg_report = await _kg_purge_user(user_id)
    pg_deleted = await _pg_purge_user(user_id)
    return {
        "nodes_deleted":         kg_report.get("nodes_deleted", 0),
        "sessions_deleted":      kg_report.get("sessions_deleted", 0),
        "user_deleted":          kg_report.get("user_deleted", 0),
        "pgvector_rows_deleted": sum(pg_deleted.values()),
        "pgvector_per_label":    pg_deleted,
    }


# retry

async def _read_unsynced_batch(
    label: str,
    *,
    batch_size: int,
) -> list[dict[str, Any]]:
    """return active_rows"""
    cfg            = _LABEL_CONFIG[label]
    content_fld    = cfg["content_field"]
    importance_fld = cfg["importance_field"]
    anchor_edge    = cfg["anchor_edge"]

    importance_expr = (
        f"coalesce(n.{importance_fld}, $importance_default)"
        if importance_fld
        else "$importance_default"
    )

    cypher = f"""
        MATCH (u:User)-[r:{anchor_edge}]->(n:{label})
        WHERE n.active           = true
          AND n.embedding_synced = false
          AND r.t_invalid IS NULL
        RETURN n.id              AS id,
               u.id              AS user_id,
               n.{content_fld}   AS content,
               {importance_expr} AS importance
        ORDER BY coalesce(n.created_at, n.timestamp, n.first_seen) ASC
        LIMIT $batch_size
    """

    return await get_client().execute_read(
        cypher,
        {
            "batch_size":         int(batch_size),
            "importance_default": float(cfg["importance_default"]),
        },
    )


async def _reconcile_row(label: str, row: dict[str, Any]) -> bool:
    """async def sync_check():     # code     return True"""
    cfg     = _LABEL_CONFIG[label]
    upsert  = cfg["upsert"]

    node_id    = row.get("id")
    user_id    = row.get("user_id")
    content    = row.get("content")
    importance = row.get("importance", cfg["importance_default"])

    if not node_id or not user_id or not content:
        logger.warning(
            "Skipping %s row with missing required field(s): "
            "id=%r user_id=%r content_present=%s",
            label, node_id, user_id, bool(content),
        )
        return False

    try:
        embedding = await embed_text(content)
    except Exception as exc:
        logger.warning(
            "Embedder failed for %s/%s: %s. Will retry next sweep.",
            label, node_id, exc,
        )
        return False

    ok = await upsert(
        user_id=user_id,
        neo4j_node_id=node_id,
        content=content,
        embedding=embedding,
        importance=float(importance),
    )
    if not ok:
        return False

    try:
        await mark_embedding_synced(label, node_id, synced=True)
        return True
    except Exception as exc:
        logger.warning(
            "pgvector upsert ok but flag flip failed for %s/%s: %s. "
            "Next sweep will retry; upsert is idempotent.",
            label, node_id, exc,
        )
        return False


async def sweep_unsynced(
    *,
    batch_size: int = 100,
    label_filter: Iterable[str] | None = None,
) -> dict[str, dict[str, int]]:
    """reconcile, batch, embed, label"""
    if label_filter is None:
        labels = sorted(_LABEL_CONFIG.keys())
    else:
        labels = sorted(set(label_filter) & set(_LABEL_CONFIG.keys()))

    report: dict[str, dict[str, int]] = {
        label: {"scanned": 0, "synced": 0, "failed": 0}
        for label in labels
    }

    for label in labels:
        try:
            batch = await _read_unsynced_batch(label, batch_size=batch_size)
        except Exception as exc:
            logger.warning(
                "Could not read unsynced batch for %s: %s. "
                "Skipping this label for the current sweep.",
                label, exc,
            )
            continue

        report[label]["scanned"] = len(batch)
        for row in batch:
            if await _reconcile_row(label, row):
                report[label]["synced"] += 1
            else:
                report[label]["failed"] += 1

        if batch:
            logger.info(
                "retry sweep %s: scanned=%d synced=%d failed=%d",
                label,
                report[label]["scanned"],
                report[label]["synced"],
                report[label]["failed"],
            )

    return report


async def sweep_until_drained(
    *,
    batch_size: int = 100,
    max_passes: int = 10,
    label_filter: Iterable[str] | None = None,
) -> dict[str, dict[str, int]]:
    """sweep_unsynced untill max_passes"""
    cumulative: dict[str, dict[str, int]] = {}
    for _ in range(max(1, int(max_passes))):
        pass_report = await sweep_unsynced(
            batch_size=batch_size, label_filter=label_filter,
        )

        for label, counts in pass_report.items():
            bucket = cumulative.setdefault(
                label, {"scanned": 0, "synced": 0, "failed": 0},
            )
            for key in ("scanned", "synced", "failed"):
                bucket[key] += counts[key]

        if all(c["scanned"] == 0 for c in pass_report.values()):
            break

    return cumulative


__all__ = [
    # dedup thresholds
    "MERGE_THRESHOLD",
    "REVIEW_THRESHOLD",
    # skip
    "sync_embedding_to_pgvector",
    "find_similar_node",
    # bridge lifecycles
    "invalidate_message_full",
    "purge_message_full",
    "purge_session_full",
    "purge_user_memory_full",
    "purge_user_full",
    # retry
    "sweep_unsynced",
    "sweep_until_drained",
]
