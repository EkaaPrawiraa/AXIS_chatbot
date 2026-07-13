"""Contracts backing Tabel v2-user-control: view, correct, and hide a memory
node through the real gateway service layer (agentic.gateway.service.memory_graph),
and delete conversation history through purge_session_full. All three run
against a live Neo4j instance, not mocks."""

from __future__ import annotations

import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio

from agentic.memory import neo4j_client as nc

from .conftest import neo4j_required

pytestmark = [pytest.mark.asyncio, neo4j_required]


@pytest_asyncio.fixture
async def subject_node(neo4j_client: nc.Neo4jClient) -> AsyncIterator[dict]:
    ns = f"pytest-usercontrol-{uuid.uuid4()}"
    user_id = f"{ns}-user"
    subject_id = f"{ns}-subject"

    await neo4j_client.execute_write(
        """
        CREATE (u:User {id: $user_id, test_namespace: $ns})
        CREATE (s:Subject {
            id: $subject_id, name: 'dosen pembimbing', role: 'dospem',
            subject_type: 'person', sensitivity_level: 'normal',
            active: true, test_namespace: $ns
        })
        CREATE (u)-[:HAS_SUBJECT {t_invalid: null}]->(s)
        """,
        {"user_id": user_id, "subject_id": subject_id, "ns": ns},
    )

    try:
        yield {"namespace": ns, "user_id": user_id, "subject_id": subject_id}
    finally:
        await neo4j_client.execute_write(
            "MATCH (n) WHERE n.test_namespace = $ns DETACH DELETE n",
            {"ns": ns},
        )


class TestMemoryNodeViewCorrectHide:
    async def test_view_lists_the_seeded_subject(
        self, neo4j_client: nc.Neo4jClient, subject_node: dict,
    ) -> None:
        from agentic.gateway.service.memory_graph import list_memory_nodes

        result = await list_memory_nodes(user_id=subject_node["user_id"], node_type="subject")

        assert any(n.id == subject_node["subject_id"] for n in result.nodes)

    async def test_correct_updates_role_without_touching_other_fields(
        self, neo4j_client: nc.Neo4jClient, subject_node: dict,
    ) -> None:
        from agentic.gateway.service.memory_graph import update_memory_node

        updated, _pg_synced = await update_memory_node(
            user_id=subject_node["user_id"],
            node_type="subject",
            node_id=subject_node["subject_id"],
            properties={"role": "dosen pembimbing skripsi"},
        )

        assert updated.properties["role"] == "dosen pembimbing skripsi"
        assert updated.properties["name"] == "dosen pembimbing"

    async def test_hide_marks_edge_invalid_and_node_inactive(
        self, neo4j_client: nc.Neo4jClient, subject_node: dict,
    ) -> None:
        from agentic.gateway.service.memory_graph import (
            archive_memory_node,
            list_memory_nodes,
        )

        touched, _pg_archived = await archive_memory_node(
            user_id=subject_node["user_id"],
            node_type="subject",
            node_id=subject_node["subject_id"],
        )
        assert touched is True

        result = await list_memory_nodes(user_id=subject_node["user_id"], node_type="subject")
        assert not any(n.id == subject_node["subject_id"] for n in result.nodes), (
            "archived subject must no longer surface via the user-facing list"
        )


@pytest_asyncio.fixture
async def session_scoped_experience(neo4j_client: nc.Neo4jClient) -> AsyncIterator[dict]:
    ns = f"pytest-purgesession-{uuid.uuid4()}"
    user_id = f"{ns}-user"
    session_id = f"{ns}-session"
    exp_id = f"{ns}-exp"

    await neo4j_client.execute_write(
        """
        CREATE (u:User {id: $user_id, test_namespace: $ns})
        CREATE (e:Experience {
            id: $exp_id, description: 'cerita yang mau dihapus dari riwayat',
            significance: 0.8, valence: -0.4, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {source_session: $session_id}]->(e)
        """,
        {"user_id": user_id, "exp_id": exp_id, "session_id": session_id, "ns": ns},
    )

    try:
        yield {"namespace": ns, "user_id": user_id, "session_id": session_id, "experience_id": exp_id}
    finally:
        await neo4j_client.execute_write(
            "MATCH (n) WHERE n.test_namespace = $ns DETACH DELETE n",
            {"ns": ns},
        )


class TestDeleteConversationHistory:
    async def test_purge_session_removes_session_scoped_experience(
        self, neo4j_client: nc.Neo4jClient, session_scoped_experience: dict,
    ) -> None:
        from agentic.memory.cross_store_sync import purge_session_full

        exp_id = session_scoped_experience["experience_id"]
        session_id = session_scoped_experience["session_id"]

        before = await neo4j_client.execute_read(
            "MATCH (e:Experience {id: $id}) RETURN e.id AS id", {"id": exp_id},
        )
        assert before, "fixture setup sanity check"

        result = await purge_session_full(session_id, message_ids=[])

        assert result["nodes_deleted"] >= 1
        after = await neo4j_client.execute_read(
            "MATCH (e:Experience {id: $id}) RETURN e.id AS id", {"id": exp_id},
        )
        assert not after, "session-scoped Experience must be gone after purge"
