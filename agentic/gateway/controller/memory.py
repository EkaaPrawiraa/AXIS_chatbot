from __future__ import annotations

from fastapi import APIRouter, Query

from agentic.gateway.model.memory import (
    MemoryGraphRelationResponse,
    MemoryNodeDeleteResponse,
    MemoryNodeListResponse,
    MemoryNodeType,
    MemoryNodeUpdateRequest,
    MemoryNodeUpdateResponse,
    MemoryPurgeResponse,
    MemoryResetResponse,
    MemorySessionPurgeRequest,
    MemorySessionPurgeResponse,
)
from agentic.gateway.service.memory_graph import (
    archive_memory_node,
    list_safe_memory_relations,
    list_memory_nodes,
    purge_session_memory,
    purge_user_account,
    reset_user_memory,
    update_memory_node,
)


router = APIRouter(prefix="/memory-nodes", tags=["memory-nodes"])


@router.get("", response_model=MemoryNodeListResponse)
async def list_nodes(
    user_id: str = Query(...),
    node_type: MemoryNodeType = Query("memory"),
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> MemoryNodeListResponse:
    return await list_memory_nodes(
        user_id=user_id,
        node_type=node_type,
        search_query=q,
        limit=limit,
        offset=offset,
    )


@router.get("/relations", response_model=MemoryGraphRelationResponse)
async def list_relations(
    user_id: str = Query(...),
    limit: int = 150,
) -> MemoryGraphRelationResponse:
    return await list_safe_memory_relations(user_id=user_id, limit=limit)


@router.patch("/{node_type}/{node_id}", response_model=MemoryNodeUpdateResponse)
async def update_node(
    node_type: MemoryNodeType,
    node_id: str,
    payload: MemoryNodeUpdateRequest,
) -> MemoryNodeUpdateResponse:
    node, pg_synced = await update_memory_node(
        user_id=payload.user_id,
        node_type=node_type,
        node_id=node_id,
        properties=payload.properties,
    )
    return MemoryNodeUpdateResponse(node=node, updated=True, pgvector_synced=pg_synced)


@router.delete("/{node_type}/{node_id}", response_model=MemoryNodeDeleteResponse)
async def delete_node(
    node_type: MemoryNodeType,
    node_id: str,
    user_id: str = Query(...),
) -> MemoryNodeDeleteResponse:
    deleted, pg_archived = await archive_memory_node(
        user_id=user_id,
        node_type=node_type,
        node_id=node_id,
    )
    return MemoryNodeDeleteResponse(
        deleted=deleted,
        archived=deleted,
        pgvector_archived=pg_archived,
    )


@router.delete("/users/{user_id}/reset", response_model=MemoryResetResponse)
async def reset_memory(user_id: str) -> MemoryResetResponse:
    report = await reset_user_memory(user_id=user_id)
    return MemoryResetResponse(
        reset=True,
        nodes_deleted=int(report.get("nodes_deleted") or 0),
        sessions_deleted=int(report.get("sessions_deleted") or 0),
        user_relationships_deleted=int(report.get("user_relationships_deleted") or 0),
        pgvector_rows_deleted=int(report.get("pgvector_rows_deleted") or 0),
        user_deleted=int(report.get("user_deleted") or 0),
    )


@router.delete("/users/{user_id}/purge", response_model=MemoryPurgeResponse)
async def purge_account(user_id: str) -> MemoryPurgeResponse:
    report = await purge_user_account(user_id=user_id)
    return MemoryPurgeResponse(
        purged=True,
        nodes_deleted=int(report.get("nodes_deleted") or 0),
        sessions_deleted=int(report.get("sessions_deleted") or 0),
        user_deleted=int(report.get("user_deleted") or 0),
        pgvector_rows_deleted=int(report.get("pgvector_rows_deleted") or 0),
    )


@router.delete("/sessions/{session_id}/purge", response_model=MemorySessionPurgeResponse)
async def purge_session(
    session_id: str,
    payload: MemorySessionPurgeRequest | None = None,
) -> MemorySessionPurgeResponse:
    message_ids = payload.message_ids if payload else []
    report = await purge_session_memory(
        session_id=session_id,
        message_ids=message_ids,
    )
    return MemorySessionPurgeResponse(
        purged=True,
        relationships_deleted=int(report.get("relationships_deleted") or 0),
        sessions_deleted=int(report.get("sessions_deleted") or 0),
        nodes_deleted=int(report.get("nodes_deleted") or 0),
        pgvector_rows_deleted=int(report.get("pgvector_rows_deleted") or 0),
        messages_processed=len(message_ids),
    )


def register_memory_routes(app) -> None:
    app.include_router(router)
