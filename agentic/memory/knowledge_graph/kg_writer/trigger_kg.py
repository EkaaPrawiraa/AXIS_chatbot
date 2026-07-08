"""trigger node, user triggers"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import (
    MERGE_THRESHOLD,
    _new_id,
    _require,
)
from agentic.memory.knowledge_graph.kg_retriever.schemas import TriggerInput
from agentic.memory.neo4j_client     import get_client
from agentic.memory.cross_store_sync import (
    find_similar_node,
    sync_embedding_to_pgvector,
)

logger = logging.getLogger(__name__)


async def write_trigger(inp: TriggerInput) -> str:
    """# on_match: #   * freq += 1 #   * last_seen = now #   * aliases += incoming_desc  # on_create: #   * aliases = inp.aliases #   * embedding_synced = False #   * pgvector_synced"""
    _require(inp.category,    "category")
    _require(inp.description, "description")
    _require(inp.user_id,     "user_id")
    _require(inp.session_id,  "session_id")

    client = get_client()
    significance = inp.significance if inp.significance is not None else 0.5

    # match fast
    existing = await client.execute_read_single(
        """
        MATCH (u:User {id: $user_id})-[:HAS_TRIGGER]->(t:Trigger)
        WHERE t.category = $category
          AND t.active   = true
          AND toLower(t.description) CONTAINS toLower($keyword)
        RETURN t.id AS id, t.frequency AS frequency, t.description AS canonical
        ORDER BY t.frequency DESC
        LIMIT 1
        """,
        {
            "user_id":  inp.user_id,
            "category": inp.category,
            "keyword":  inp.description[:30],
        },
    )

    # skip fast path
    if existing is None and inp.embedding is not None:
        similar = await find_similar_node(
            label="Trigger",
            embedding=inp.embedding,
            user_id=inp.user_id,
        )
        if similar and similar["similarity"] >= MERGE_THRESHOLD:
            existing = {
                "id":        similar["id"],
                "frequency": None,                 # not needed for the merge
                "canonical": similar["description"],
            }
            logger.debug(
                "Trigger cosine-merged: %.2f similarity to %s",
                similar["similarity"], similar["id"],
            )

    if existing:
        # build aliases list: new phrasing + caller-supplied aliases. drop canonical desc; Cypher dedup ex. aliases.
        canonical = existing["canonical"]
        candidate_aliases: list[str] = []
        if inp.description and inp.description != canonical:
            candidate_aliases.append(inp.description)
        for alias in (inp.aliases or []):
            if alias and alias != canonical and alias not in candidate_aliases:
                candidate_aliases.append(alias)

        await client.execute_write(
            """
            MATCH (t:Trigger {id: $id})
            SET t.frequency = t.frequency + 1,
                t.last_seen = datetime(),
                t.significance = CASE
                    WHEN coalesce(t.significance, 0.5) < $significance THEN $significance
                    WHEN coalesce(t.significance, 0.5) < 0.95 THEN coalesce(t.significance, 0.5) + 0.05
                    ELSE 1.0
                END,
                t.aliases   = [
                    alias IN coalesce(t.aliases, []) + $candidate_aliases
                    WHERE alias IS NOT NULL
                      AND alias <> t.description
                    | alias
                ]
            WITH t
            // Collapse aliases to unique values while preserving first-seen order.
            UNWIND t.aliases AS a
            WITH t, collect(DISTINCT a) AS deduped
            SET t.aliases = deduped
            WITH t
            MATCH (u:User {id: $user_id})-[r:HAS_TRIGGER]->(t)
            WHERE r.t_invalid IS NULL
              AND $message_id IS NOT NULL
              AND NOT $message_id IN coalesce(r.source_messages, [])
            SET r.source_messages = coalesce(r.source_messages, []) + $message_id
            """,
            {
                "id":                 existing["id"],
                "candidate_aliases":  candidate_aliases,
                "user_id":            inp.user_id,
                "message_id":         inp.source_message_id,
                "significance":       significance,
            },
        )
        logger.debug(
            "Trigger frequency incremented: %s (added %d alias(es))",
            existing["id"], len(candidate_aliases),
        )
        return existing["id"]

    # buat nyimpen config
    node_id = _new_id()
    await client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (t:Trigger {
            id:                $id,
            category:          $category,
            description:       $description,
            significance:      $significance,
            frequency:         1,
            first_seen:        datetime(),
            last_seen:         datetime(),
            active:            true,
            aliases:           $aliases,
            embedding_synced:  false,
            sensitivity_level: $sensitivity_level
        })
        CREATE (u)-[:HAS_TRIGGER {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(t)
        RETURN t.id AS id
        """,
        {
            "user_id":           inp.user_id,
            "session_id":        inp.session_id,
            "id":                node_id,
            "category":          inp.category,
            "description":       inp.description,
            "significance":      significance,
            "aliases":           list(inp.aliases or []),
            "sensitivity_level": inp.sensitivity_level,
            "confidence":        inp.confidence,
            "message_id":        inp.source_message_id,
        },
    )

    # mirrors into pgvector, flip on success.
    await sync_embedding_to_pgvector(
        label="Trigger",
        node_id=node_id,
        user_id=inp.user_id,
        content=inp.description,
        embedding=inp.embedding,
        importance=significance,
    )

    logger.debug("Trigger written: %s", node_id)
    return node_id
