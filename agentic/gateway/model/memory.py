from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MemoryNodeType = Literal[
    "subject",
    "experience",
    "emotion",
    "trigger",
    "thought",
    "behaviour",
    "behavior",
    "topic",
    "memory",
    "person",    # deprecated alias for "subject" — normalised in gateway/service/memory_graph.py
]


class MemoryNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    label: str
    title: str
    preview: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    editable_fields: list[str] = Field(default_factory=list)
    enum_fields: dict[str, list[str]] = Field(default_factory=dict)
    embedding_synced: bool | None = None
    updated_at: str | None = None


class MemoryNodeListResponse(BaseModel):
    nodes: list[MemoryNode]
    node_type: str
    total: int


class MemoryGraphRelation(BaseModel):
    id: str
    source_id: str
    source_type: str
    source_title: str
    target_id: str
    target_type: str
    target_title: str
    relation_type: str
    label: str
    confidence: float | None = None


class MemoryGraphRelationResponse(BaseModel):
    relations: list[MemoryGraphRelation]
    total: int


class MemoryNodeUpdateRequest(BaseModel):
    user_id: str
    properties: dict[str, Any]


class MemoryNodeUpdateResponse(BaseModel):
    node: MemoryNode
    updated: bool
    pgvector_synced: bool | None = None


class MemoryNodeDeleteResponse(BaseModel):
    deleted: bool
    archived: bool
    pgvector_archived: int = 0


class MemoryResetResponse(BaseModel):
    reset: bool
    nodes_deleted: int = 0
    sessions_deleted: int = 0
    user_relationships_deleted: int = 0
    pgvector_rows_deleted: int = 0
    user_deleted: int = 0


class MemoryPurgeResponse(BaseModel):
    purged: bool
    nodes_deleted: int = 0
    sessions_deleted: int = 0
    user_deleted: int = 0
    pgvector_rows_deleted: int = 0


class MemorySessionPurgeRequest(BaseModel):
    message_ids: list[str] = Field(default_factory=list)

    @field_validator("message_ids", mode="before")
    @classmethod
    def default_message_ids(cls, value: Any) -> list[str] | Any:
        if value is None:
            return []
        return value


class MemorySessionPurgeResponse(BaseModel):
    purged: bool
    relationships_deleted: int = 0
    sessions_deleted: int = 0
    nodes_deleted: int = 0
    pgvector_rows_deleted: int = 0
    messages_processed: int = 0
