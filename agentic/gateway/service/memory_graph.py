from __future__ import annotations

import json
from typing import Any

from agentic.agent.nodes.input_guardrail import load_input_rules
from agentic.gateway.model.memory import (
    MemoryGraphRelation,
    MemoryGraphRelationResponse,
    MemoryNode,
    MemoryNodeListResponse,
)
from agentic.memory.cross_store_sync import (
    purge_session_full,
    purge_user_full,
    purge_user_memory_full,
    sync_embedding_to_pgvector,
)
from agentic.memory.knowledge_graph.kg_modifier.update_node import update_node_property
from agentic.memory.neo4j_client import get_client
from agentic.memory.pg_vector import archive_node, embed_text


TRIGGER_CATEGORIES = ["academic", "social", "family", "work", "health", "financial", "other"]
BEHAVIOR_CATEGORIES = [
    "avoidance",
    "rumination",
    "exercise",
    "substance_use",
    "social_withdrawal",
    "help_seeking",
    "other",
]
TOPIC_CATEGORIES = [
    "academic",
    "social",
    "family",
    "career",
    "health",
    "financial",
    "identity",
    "mental_health",
    "other",
]
SENSITIVITY_LEVELS = ["normal", "sensitive", "trauma"]


NODE_CONFIG: dict[str, dict[str, Any]] = {
    "experience": {
        "label": "Experience",
        "edge": "EXPERIENCED",
        "editable": ["description", "sensitivity_level"],
        "content_field": "description",
        "importance_field": "significance",
        "title_field": "description",
        "enums": {"sensitivity_level": SENSITIVITY_LEVELS},
    },
    "emotion": {"label": "Emotion", "edge": "FELT", "editable": ["label"], "title_field": "label"},
    "trigger": {
        "label": "Trigger",
        "edge": "HAS_TRIGGER",
        "editable": ["description", "category", "aliases", "sensitivity_level"],
        "content_field": "description",
        "title_field": "description",
        "enums": {"category": TRIGGER_CATEGORIES, "sensitivity_level": SENSITIVITY_LEVELS},
    },
    "thought": {
        "label": "Thought",
        "edge": "HAS_THOUGHT",
        "editable": ["content", "sensitivity_level"],
        "content_field": "content",
        "importance_field": "believability",
        "title_field": "content",
        "enums": {"sensitivity_level": SENSITIVITY_LEVELS},
    },
    "behaviour": {
        "label": "Behavior",
        "edge": "EXHIBITED",
        "editable": ["description", "category", "sensitivity_level"],
        "title_field": "description",
        "enums": {"category": BEHAVIOR_CATEGORIES, "sensitivity_level": SENSITIVITY_LEVELS},
    },
    "subject": {
        "label": "Subject",
        "edge": "HAS_SUBJECT",
        "editable": ["name", "role", "subject_type", "sensitivity_level"],
        "title_field": "name",
        "enums": {"sensitivity_level": SENSITIVITY_LEVELS},
    },
    "topic": {
        "label": "Topic",
        "edge": "HAS_RECURRING_THEME",
        "editable": ["name"],
        "title_field": "name",
        "enums": {"category": TOPIC_CATEGORIES},
    },
    "memory": {
        "label": "Memory",
        "edge": "HAS_MEMORY",
        "editable": ["summary", "sensitivity_level"],
        "content_field": "summary",
        "importance_field": "importance",
        "title_field": "summary",
        "enums": {"sensitivity_level": SENSITIVITY_LEVELS},
    },
}

NODE_CONFIG["behavior"] = NODE_CONFIG["behaviour"]
NODE_CONFIG["person"] = NODE_CONFIG["subject"]  # backward compat: old clients send node_type=person
EMBEDDABLE_LABELS = {"Experience", "Trigger", "Thought", "Memory"}


def normalize_type(node_type: str) -> str:
    key = (node_type or "").strip().lower()
    if key == "behavior":
        key = "behaviour"
    if key == "person":
        key = "subject"   # person is the old canonical name; subject is the current one
    if key not in NODE_CONFIG:
        raise ValueError(f"unsupported memory node type: {node_type}")
    return key


def _cfg(node_type: str) -> dict[str, Any]:
    return NODE_CONFIG[normalize_type(node_type)]


def _public_type(label: str) -> str:
    return "behaviour" if label == "Behavior" else label.lower()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    iso = getattr(value, "iso_format", None)
    if callable(iso):
        return iso()
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    if value.__class__.__module__.startswith("neo4j."):
        return str(value)
    return value


def _unwrap_json_text(value: str) -> str:
    """If a stored text field is accidentally JSON-wrapped (e.g. '{"summary":"..."}'),
    extract the actual string value. Returns the original value if it is not JSON."""
    stripped = value.strip()
    if not stripped.startswith("{"):
        return stripped
    try:
        data = json.loads(stripped)
        for key in ("summary", "text", "content", "description", "result"):
            if isinstance(data.get(key), str) and data[key].strip():
                return data[key].strip()
        for val in data.values():
            if isinstance(val, str) and len(val) > 10:
                return val.strip()
    except (json.JSONDecodeError, Exception):
        pass
    return stripped


def _to_node(props: dict[str, Any], cfg: dict[str, Any]) -> MemoryNode:
    props = _json_safe(props)
    label = cfg["label"]
    title_field = cfg.get("title_field")
    raw_title = str(props.get(title_field) or props.get("id") or "").strip()
    title = _unwrap_json_text(raw_title)
    preview = ""
    for field in ("summary", "description", "content", "label", "name", "role"):
        raw_value = str(props.get(field) or "").strip()
        if raw_value:
            preview = _unwrap_json_text(raw_value)[:180]
            break
    return MemoryNode(
        id=str(props.get("id") or ""),
        type=_public_type(label),
        label=label,
        title=title[:100],
        preview=preview,
        properties=props,
        editable_fields=list(cfg.get("editable") or []),
        enum_fields=dict(cfg.get("enums") or {}),
        embedding_synced=props.get("embedding_synced"),
        updated_at=str(props.get("updated_at")) if props.get("updated_at") else None,
    )


def _node_title(props: dict[str, Any], label: str) -> str:
    props = _json_safe(props)
    for field in ("summary", "description", "content", "name", "label", "role"):
        value = str(props.get(field) or "").strip()
        if value:
            return value[:100]
    return str(props.get("id") or label)


def _to_relation(row: dict[str, Any]) -> MemoryGraphRelation:
    source_props = _json_safe(row["source_props"])
    target_props = _json_safe(row["target_props"])
    relation_type = str(row["relation_type"])
    source_type = _public_type(str(row["source_label"]))
    target_type = _public_type(str(row["target_label"]))
    return MemoryGraphRelation(
        id=f"{source_type}:{source_props.get('id')}:{relation_type}:{target_type}:{target_props.get('id')}",
        source_id=str(source_props.get("id") or ""),
        source_type=source_type,
        source_title=_node_title(source_props, str(row["source_label"])),
        target_id=str(target_props.get("id") or ""),
        target_type=target_type,
        target_title=_node_title(target_props, str(row["target_label"])),
        relation_type=relation_type,
        label=str(row["label"]),
        confidence=row.get("confidence"),
    )


async def list_safe_memory_relations(
    *,
    user_id: str,
    limit: int = 150,
) -> MemoryGraphRelationResponse:
    rows = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[r:HAS_MEMORY]->(m:Memory)
        WHERE r.t_invalid IS NULL AND coalesce(m.active, true) = true
        RETURN properties(u) AS source_props, "User" AS source_label,
               properties(m) AS target_props, "Memory" AS target_label,
               type(r) AS relation_type, "has memory" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[r:HAS_RECURRING_THEME]->(t:Topic)
        WHERE r.t_invalid IS NULL
        RETURN properties(u) AS source_props, "User" AS source_label,
               properties(t) AS target_props, "Topic" AS target_label,
               type(r) AS relation_type, "recurring theme" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[r:HAS_SUBJECT]->(p:Subject)
        WHERE r.t_invalid IS NULL
        RETURN properties(u) AS source_props, "User" AS source_label,
               properties(p) AS target_props, "Subject" AS target_label,
               type(r) AS relation_type, "subject" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)-[r:INVOLVES_SUBJECT]->(p:Subject)<-[:HAS_SUBJECT]-(u)
        WHERE r.t_invalid IS NULL AND coalesce(e.active, true) = true
        RETURN properties(e) AS source_props, "Experience" AS source_label,
               properties(p) AS target_props, "Subject" AS target_label,
               type(r) AS relation_type, "involves" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)-[r:RELATED_TO_TOPIC]->(t:Topic)<-[:HAS_RECURRING_THEME]-(u)
        WHERE r.t_invalid IS NULL AND coalesce(e.active, true) = true
        RETURN properties(e) AS source_props, "Experience" AS source_label,
               properties(t) AS target_props, "Topic" AS target_label,
               type(r) AS relation_type, "about" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)-[r:TRIGGERED_BY]->(t:Trigger)<-[:HAS_TRIGGER]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(e.active, true) = true
          AND coalesce(t.active, true) = true
        RETURN properties(e) AS source_props, "Experience" AS source_label,
               properties(t) AS target_props, "Trigger" AS target_label,
               type(r) AS relation_type, "linked to" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)-[r:TRIGGERED_EMOTION]->(em:Emotion)<-[:FELT]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(e.active, true) = true
          AND coalesce(em.active, true) = true
        RETURN properties(e) AS source_props, "Experience" AS source_label,
               properties(em) AS target_props, "Emotion" AS target_label,
               type(r) AS relation_type, "felt" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)-[r:ACTIVATED_THOUGHT]->(th:Thought)<-[:HAS_THOUGHT]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(em.active, true) = true
          AND coalesce(th.active, true) = true
        RETURN properties(em) AS source_props, "Emotion" AS source_label,
               properties(th) AS target_props, "Thought" AS target_label,
               type(r) AS relation_type, "activated" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)-[r:LED_TO_BEHAVIOR]->(b:Behavior)<-[:EXHIBITED]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(em.active, true) = true
          AND coalesce(b.active, true) = true
        RETURN properties(em) AS source_props, "Emotion" AS source_label,
               properties(b) AS target_props, "Behavior" AS target_label,
               type(r) AS relation_type, "led to" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(th:Thought)-[r:LED_TO_BEHAVIOR]->(b:Behavior)<-[:EXHIBITED]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(th.active, true) = true
          AND coalesce(b.active, true) = true
        RETURN properties(th) AS source_props, "Thought" AS source_label,
               properties(b) AS target_props, "Behavior" AS target_label,
               type(r) AS relation_type, "led to" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)-[r:RELATED_TO_TOPIC]->(t:Topic)<-[:HAS_RECURRING_THEME]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(em.active, true) = true
        RETURN properties(em) AS source_props, "Emotion" AS source_label,
               properties(t) AS target_props, "Topic" AS target_label,
               type(r) AS relation_type, "about" AS label,
               r.confidence AS confidence

        UNION ALL

        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(th:Thought)-[r:RELATED_TO_TOPIC]->(t:Topic)<-[:HAS_RECURRING_THEME]-(u)
        WHERE r.t_invalid IS NULL
          AND coalesce(th.active, true) = true
        RETURN properties(th) AS source_props, "Thought" AS source_label,
               properties(t) AS target_props, "Topic" AS target_label,
               type(r) AS relation_type, "about" AS label,
               r.confidence AS confidence

        LIMIT $limit
        """,
        {"user_id": user_id, "limit": max(1, min(int(limit or 150), 300))},
    )
    relations = [_to_relation(row) for row in rows]
    return MemoryGraphRelationResponse(relations=relations, total=len(relations))


async def list_memory_nodes(
    *,
    user_id: str,
    node_type: str,
    search_query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MemoryNodeListResponse:
    key = normalize_type(node_type)
    cfg = NODE_CONFIG[key]
    label = cfg["label"]
    edge = cfg["edge"]
    editable = cfg["editable"]
    search_fields = [field for field in editable if field != "aliases"] + ["summary", "name"]
    search_predicate = " OR ".join(
        f"toLower(toString(coalesce(n.{field}, ''))) CONTAINS toLower($q)"
        for field in sorted(set(search_fields))
    )
    active_predicate = "coalesce(n.active, true) = true" if label != "Topic" else "true"
    rows = await get_client().execute_read(
        f"""
        MATCH (u:User {{id: $user_id}})-[r:{edge}]->(n:{label})
        WHERE r.t_invalid IS NULL
          AND {active_predicate}
          AND ($q = '' OR {search_predicate})
        WITH n
        ORDER BY coalesce(n.updated_at, n.last_accessed, n.last_seen, n.timestamp, n.created_at, n.first_seen) DESC
        SKIP $offset
        LIMIT $limit
        RETURN properties(n) AS props
        """,
        {
            "user_id": user_id,
            "q": (search_query or "").strip(),
            "limit": max(1, min(int(limit or 50), 100)),
            "offset": max(0, int(offset or 0)),
        },
    )
    nodes = [_to_node(row["props"], cfg) for row in rows]
    return MemoryNodeListResponse(nodes=nodes, node_type=key, total=len(nodes))


async def get_memory_node(*, user_id: str, node_type: str, node_id: str) -> MemoryNode | None:
    cfg = _cfg(node_type)
    rows = await get_client().execute_read(
        f"""
        MATCH (u:User {{id: $user_id}})-[r:{cfg["edge"]}]->(n:{cfg["label"]} {{id: $node_id}})
        WHERE r.t_invalid IS NULL
        RETURN properties(n) AS props
        LIMIT 1
        """,
        {"user_id": user_id, "node_id": node_id},
    )
    return _to_node(rows[0]["props"], cfg) if rows else None


def _reject_injection_content(cfg: dict[str, Any], updates: dict[str, Any]) -> None:
    """
    Reject free-text edits that match a known jailbreak/prompt-injection
    pattern (the same JAILBREAK_PATTERNS list input_guardrail_node uses
    for live chat turns -- see guardrails/input_validation.yaml).

    Memory node content is fed back into every future turn's LLM context
    via context_builder, so injected instructions saved here would be an
    indirect prompt-injection vector with no legitimate reason to exist
    in a personal memory note. Crisis keywords are deliberately NOT
    checked here -- storing a user's own crisis history as memory is
    legitimate content, not something to block.
    """
    enum_fields = set((cfg.get("enums") or {}).keys())
    rules = load_input_rules()
    for key, value in updates.items():
        if key in enum_fields:
            continue
        texts = [value] if isinstance(value, str) else (
            [str(v) for v in value] if isinstance(value, list) else []
        )
        for text in texts:
            for pat in rules.jailbreak_patterns:
                if pat.search(text):
                    raise ValueError(f"{key} contains disallowed content")


def _sanitize_updates(cfg: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    editable = set(cfg["editable"])
    updates: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in editable:
            continue
        if key == "aliases":
            if isinstance(value, str):
                value = [part.strip() for part in value.split(",") if part.strip()]
            elif isinstance(value, list):
                value = [str(part).strip() for part in value if str(part).strip()]
            else:
                value = []
        elif isinstance(value, str):
            value = value.strip()
        updates[key] = value
    if not updates:
        raise ValueError("no editable properties supplied")
    for field, allowed in dict(cfg.get("enums") or {}).items():
        if field in updates and updates[field] not in allowed:
            raise ValueError(f"{field} must be one of {allowed}")
    _reject_injection_content(cfg, updates)
    return updates


async def update_memory_node(
    *,
    user_id: str,
    node_type: str,
    node_id: str,
    properties: dict[str, Any],
) -> tuple[MemoryNode, bool | None]:
    cfg = _cfg(node_type)
    existing = await get_memory_node(user_id=user_id, node_type=node_type, node_id=node_id)
    if existing is None:
        raise ValueError("memory node not found")
    updates = _sanitize_updates(cfg, properties)
    label = cfg["label"]
    content_field = cfg.get("content_field")
    content_changed = bool(content_field and content_field in updates)
    if content_changed:
        updates["embedding_synced"] = False
    if label == "Topic" and "name" in updates:
        updates["name_key"] = str(updates["name"]).lower()

    await update_node_property(label, node_id, updates)

    pg_synced: bool | None = None
    if content_changed and label in EMBEDDABLE_LABELS:
        content = str(updates[content_field])
        importance_field = cfg.get("importance_field")
        importance = existing.properties.get(importance_field, 0.5) if importance_field else 0.5
        try:
            embedding = await embed_text(content)
        except Exception:
            embedding = None
        pg_synced = await sync_embedding_to_pgvector(
            label=label,
            node_id=node_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            importance=float(importance or 0.5),
        )

    updated = await get_memory_node(user_id=user_id, node_type=node_type, node_id=node_id)
    if updated is None:
        raise ValueError("memory node not found after update")
    return updated, pg_synced


async def archive_memory_node(*, user_id: str, node_type: str, node_id: str) -> tuple[bool, int]:
    cfg = _cfg(node_type)
    label = cfg["label"]
    deactivate_node = label not in {"Subject", "Person", "Topic"}
    rows = await get_client().execute_write(
        f"""
        MATCH (u:User {{id: $user_id}})-[r:{cfg["edge"]}]->(n:{label} {{id: $node_id}})
        WHERE r.t_invalid IS NULL
        SET r.t_invalid = datetime(),
            r.invalidation_reason = 'user_deleted_memory_node'
        WITH n
        FOREACH (_ IN CASE WHEN $deactivate_node THEN [1] ELSE [] END |
            SET n.active = false,
                n.deactivated_at = datetime(),
                n.deactivation_reason = 'user_deleted_memory_node'
        )
        RETURN count(n) AS touched
        """,
        {"user_id": user_id, "node_id": node_id, "deactivate_node": deactivate_node},
    )
    if not rows or int(rows[0].get("touched") or 0) == 0:
        return False, 0
    pg_archived = 0
    if label in EMBEDDABLE_LABELS:
        pg_archived = await archive_node(label, node_id)
    return True, pg_archived


async def reset_user_memory(*, user_id: str) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")
    return await purge_user_memory_full(user_id)


async def purge_user_account(*, user_id: str) -> dict[str, Any]:
    """Fully remove a user's KG node/relationships and pgvector rows (account deletion)."""
    if not user_id:
        raise ValueError("user_id is required")
    return await purge_user_full(user_id)


async def purge_session_memory(*, session_id: str, message_ids: list[str]) -> dict[str, Any]:
    if not session_id:
        raise ValueError("session_id is required")
    return await purge_session_full(session_id, message_ids=message_ids)
