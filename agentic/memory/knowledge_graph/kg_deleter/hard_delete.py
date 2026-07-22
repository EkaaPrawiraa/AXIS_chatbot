"""hard delete: edges, nodes."""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client
from agentic.memory.knowledge_graph.kg_deleter._common import DERIVED_LABELS

logger = logging.getLogger(__name__)


# delete it

async def purge_message(message_id: str) -> dict[str, Any]:
    """hard_del()"""
    if not message_id:
        raise ValueError("message_id is required")

    client = get_client()

    # buat list ngosел
    candidates = await client.execute_read(
        """
        MATCH (src)-[r]->(dst)
        WHERE $message_id IN coalesce(r.source_messages, [])
        UNWIND [src, dst] AS n
        RETURN DISTINCT n.id AS id
        """,
        {"message_id": message_id},
    )
    candidate_ids = [row["id"] for row in candidates]

    # `del e['source_messages']`
    edge_report = await client.execute_write(
        """
        MATCH (src)-[r]->(dst)
        WHERE $message_id IN coalesce(r.source_messages, [])
        WITH r,
             [m IN coalesce(r.source_messages, []) WHERE m <> $message_id] AS remaining
        FOREACH (_ IN CASE WHEN size(remaining) = 0 THEN [1] ELSE [] END |
            DELETE r
        )
        WITH r, remaining
        WHERE r IS NOT NULL
        SET r.source_messages = remaining
        RETURN count(r) AS edges_kept_with_pruned_provenance
        """,
        {"message_id": message_id},
    )
    edges_kept = (
        edge_report[0]["edges_kept_with_pruned_provenance"]
        if edge_report else 0
    )

    # ambil id
    deleted_rows: list[dict[str, Any]] = []
    if candidate_ids:
        deleted_rows = await client.execute_write(
            """
            MATCH (n)
            WHERE n.id IN $ids
              AND any(label IN labels(n) WHERE label IN $derived_labels)
              AND NOT EXISTS { MATCH (n)<-[]-() }
            WITH n,
                 [l IN labels(n) WHERE l IN $derived_labels][0] AS label,
                 n.id AS id
            DETACH DELETE n
            RETURN id, label
            """,
            {
                "ids":            candidate_ids,
                "derived_labels": sorted(DERIVED_LABELS),
            },
        ) or []

    report = {
        "edges_with_pruned_provenance": edges_kept,
        "nodes_deleted":                len(deleted_rows),
        "deleted_rows":                 deleted_rows,
    }
    logger.info(
        "purge_message(%s) -> edges_kept=%d nodes_deleted=%d",
        message_id, edges_kept, len(deleted_rows),
    )
    return report


# del sess

async def purge_session(session_id: str) -> dict[str, Any]:
    """hard_del, preserve_node."""
    if not session_id:
        raise ValueError("session_id is required")

    client = get_client()

    candidates = await client.execute_read(
        """
        MATCH (src)-[r]->(dst)
        WHERE r.source_session = $session_id
           OR r.source_session_id = $session_id
        UNWIND [src, dst] AS n
        RETURN DISTINCT n.id AS id
        UNION
        MATCH (n)
        WHERE n.source_session = $session_id
           OR n.source_session_id = $session_id
        RETURN DISTINCT n.id AS id
        """,
        {"session_id": session_id},
    )
    candidate_ids = [row["id"] for row in candidates if row.get("id")]

    rel_report = await client.execute_write(
        """
        MATCH ()-[r]->()
        WHERE (r.source_session = $session_id
           OR r.source_session_id = $session_id)
          AND size(coalesce(r.source_messages, [])) = 0
        WITH collect(r) AS rels
        FOREACH (rel IN rels | DELETE rel)
        RETURN size(rels) AS relationships_deleted
        """,
        {"session_id": session_id},
    )
    relationships_deleted = int(rel_report[0]["relationships_deleted"]) if rel_report else 0

    session_report = await client.execute_write(
        """
        MATCH (s:Session {id: $session_id})
        WITH collect(s) AS sessions
        FOREACH (session IN sessions | DETACH DELETE session)
        RETURN size(sessions) AS sessions_deleted
        """,
        {"session_id": session_id},
    )
    sessions_deleted = int(session_report[0]["sessions_deleted"]) if session_report else 0

    deleted_rows: list[dict[str, Any]] = []
    if candidate_ids:
        deleted_rows = await client.execute_write(
            """
            MATCH (n)
            WHERE n.id IN $ids
              AND any(label IN labels(n) WHERE label IN $derived_labels)
              AND NOT EXISTS { MATCH (n)<-[]-() }
            WITH n,
                 [l IN labels(n) WHERE l IN $derived_labels][0] AS label,
                 n.id AS id
            DETACH DELETE n
            RETURN id, label
            """,
            {
                "ids": candidate_ids,
                "derived_labels": sorted(DERIVED_LABELS),
            },
        ) or []

    report = {
        "relationships_deleted": relationships_deleted,
        "sessions_deleted": sessions_deleted,
        "nodes_deleted": len(deleted_rows),
        "deleted_rows": deleted_rows,
    }
    logger.info("purge_session(%s) -> %s", session_id, report)
    return report


async def purge_user_memory(user_id: str) -> dict[str, int]:
    """hard-delete, preserve, User."""
    if not user_id:
        raise ValueError("user_id is required")

    client = get_client()

    report = await client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
        OPTIONAL MATCH (u)-[]-(n)
        WHERE any(label IN labels(n) WHERE label IN $derived_labels)
        OPTIONAL MATCH (p:Subject {owner_user_id: $user_id})

        WITH u,
             [session IN collect(DISTINCT s) WHERE session IS NOT NULL] AS sessions,
             collect(DISTINCT n) AS derived_nodes,
             collect(DISTINCT p) AS subjects

        // UNWIND on an empty list silently drops the whole row (unlike
        // OPTIONAL MATCH, which preserves nulls) -- guard both unwinds
        // below so a user with zero Session nodes, or zero derived facts
        // at all (e.g. a brand new account), doesn't make this entire
        // query return no rows.
        UNWIND (CASE WHEN size(sessions) = 0 THEN [null] ELSE sessions END) AS sess
        OPTIONAL MATCH (sess)-[]-(m)
        WHERE sess IS NOT NULL AND any(label IN labels(m) WHERE label IN $derived_labels)

        WITH u, sessions, derived_nodes, subjects,
             collect(DISTINCT m) AS session_derived

        WITH u, sessions, derived_nodes + subjects + session_derived AS candidates
        UNWIND (CASE WHEN size(candidates) = 0 THEN [null] ELSE candidates END) AS candidate
        WITH u, sessions, [c IN collect(DISTINCT candidate) WHERE c IS NOT NULL] AS raw_to_delete
        WITH u, sessions, [x IN raw_to_delete WHERE x IS NOT NULL] AS to_delete

        OPTIONAL MATCH (u)-[user_rel]-()

        WITH u, sessions, to_delete,
             [rel IN collect(DISTINCT user_rel) WHERE rel IS NOT NULL] AS user_rels,
             size(to_delete) AS derived_count,
             size(sessions) AS session_count

        FOREACH (rel IN user_rels | DELETE rel)
        FOREACH (n IN to_delete | DETACH DELETE n)
        FOREACH (s IN sessions | DETACH DELETE s)

        RETURN derived_count AS nodes_deleted,
               session_count AS sessions_deleted,
               size(user_rels) AS user_relationships_deleted
        """,
        {
            "user_id": user_id,
            "derived_labels": sorted(DERIVED_LABELS),
        },
    )

    summary = (
        {
            "nodes_deleted": report[0]["nodes_deleted"],
            "sessions_deleted": report[0]["sessions_deleted"],
            "user_relationships_deleted": report[0]["user_relationships_deleted"],
            "user_deleted": 0,
        }
        if report else
        {
            "nodes_deleted": 0,
            "sessions_deleted": 0,
            "user_relationships_deleted": 0,
            "user_deleted": 0,
        }
    )
    logger.warning("purge_user_memory(%s) executed -> %s", user_id, summary)
    return summary


async def purge_user(user_id: str) -> dict[str, int]:
    """del-hard"""
    if not user_id:
        raise ValueError("user_id is required")

    client = get_client()

    report = await client.execute_write(
        """
        // u must be matched on its own, separately from the session
        // lookup below. Combining them into one OPTIONAL MATCH (u)-[:HAD_SESSION]->(s)
        // means Cypher treats u as introduced BY that same optional
        // pattern -- if the user has zero Session nodes, the whole
        // pattern fails to match and u itself becomes null too, not just
        // s. That silently no-ops this entire purge (nothing deleted,
        // not even the User node) for any account that never completed a
        // full chat session before being deleted.
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
        // Derived nodes owned by the user (any of the seven labels)
        OPTIONAL MATCH (u)-[]-(n)
        WHERE any(label IN labels(n) WHERE label IN $derived_labels)
        // Subject nodes scoped to this owner
        OPTIONAL MATCH (p:Subject {owner_user_id: $user_id})

        WITH u,
             collect(DISTINCT s) AS sessions,
             collect(DISTINCT n) AS derived_nodes,
             collect(DISTINCT p) AS subjects

        // Derived nodes hanging off owned sessions (e.g. Memory linked
        // only via Session, not directly via User). UNWIND on an empty
        // list silently drops the whole row (unlike OPTIONAL MATCH, which
        // preserves nulls) -- without the CASE guard, a user with zero
        // Session nodes (never completed a full chat session before
        // deleting their account) would make this entire query return no
        // rows, so nothing gets deleted at all, not even the User node.
        UNWIND (CASE WHEN size(sessions) = 0 THEN [null] ELSE sessions END) AS sess
        OPTIONAL MATCH (sess)-[]-(m)
        WHERE sess IS NOT NULL AND any(label IN labels(m) WHERE label IN $derived_labels)

        WITH u, sessions, derived_nodes, subjects,
             collect(DISTINCT m) AS session_derived

        WITH u,
             sessions,
             [x IN derived_nodes + subjects + session_derived WHERE x IS NOT NULL] AS to_delete

        // Tally before deleting so we can return counts
        WITH u, sessions, to_delete,
             size(to_delete) AS derived_count,
             size(sessions)  AS session_count

        FOREACH (n IN to_delete | DETACH DELETE n)
        FOREACH (s IN sessions  | DETACH DELETE s)
        DETACH DELETE u

        RETURN derived_count AS nodes_deleted,
               session_count AS sessions_deleted
        """,
        {
            "user_id":        user_id,
            "derived_labels": sorted(DERIVED_LABELS),
        },
    )

    summary = (
        {
            "nodes_deleted":    report[0]["nodes_deleted"],
            "sessions_deleted": report[0]["sessions_deleted"],
            "user_deleted":     1,
        }
        if report else
        {
            "nodes_deleted":    0,
            "sessions_deleted": 0,
            "user_deleted":     0,
        }
    )
    logger.warning(
        "purge_user(%s) executed (Neo4j half of right-to-erasure) -> %s",
        user_id, summary,
    )
    return summary
