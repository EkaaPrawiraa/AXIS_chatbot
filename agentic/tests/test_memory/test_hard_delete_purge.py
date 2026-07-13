"""`tes reg`"""
from __future__ import annotations

import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio

from agentic.memory import neo4j_client as nc
from agentic.memory.knowledge_graph.kg_deleter.hard_delete import (
    purge_user,
    purge_user_memory,
)

from .conftest import neo4j_required

pytestmark = [pytest.mark.asyncio, neo4j_required]


@pytest_asyncio.fixture
async def user_with_no_sessions(neo4j_client: nc.Neo4jClient) -> AsyncIterator[dict]:
    """buat nyimpan config"""
    ns = f"pytest-nosession-{uuid.uuid4()}"
    user_id = f"{ns}-user"
    exp_id = f"{ns}-exp"

    await neo4j_client.execute_write(
        """
        CREATE (u:User {id: $user_id, test_namespace: $ns})
        CREATE (e:Experience {
            id: $exp_id, description: 'test purge regression',
            significance: 0.9, valence: -0.5, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED]->(e)
        """,
        {"user_id": user_id, "exp_id": exp_id, "ns": ns},
    )

    try:
        yield {"namespace": ns, "user_id": user_id, "experience_id": exp_id}
    finally:
        await neo4j_client.execute_write(
            "MATCH (n) WHERE n.test_namespace = $ns DETACH DELETE n",
            {"ns": ns},
        )


async def _user_exists(client: nc.Neo4jClient, user_id: str) -> bool:
    rows = await client.execute_read(
        "MATCH (u:User {id: $user_id}) RETURN u.id AS id", {"user_id": user_id},
    )
    return bool(rows)


class TestPurgeUserNoSessions:
    async def test_purge_user_deletes_user_with_zero_sessions(
        self, neo4j_client: nc.Neo4jClient, user_with_no_sessions: dict,
    ) -> None:
        user_id = user_with_no_sessions["user_id"]
        assert await _user_exists(neo4j_client, user_id), "fixture setup sanity check"

        result = await purge_user(user_id)

        assert result["nodes_deleted"] == 1
        assert result["sessions_deleted"] == 0
        assert result["user_deleted"] == 1
        assert not await _user_exists(neo4j_client, user_id)

    async def test_purge_user_memory_deletes_derived_nodes_keeps_user(
        self, neo4j_client: nc.Neo4jClient, user_with_no_sessions: dict,
    ) -> None:
        user_id = user_with_no_sessions["user_id"]
        exp_id = user_with_no_sessions["experience_id"]

        result = await purge_user_memory(user_id)

        assert result["nodes_deleted"] == 1
        assert result["sessions_deleted"] == 0
        assert await _user_exists(neo4j_client, user_id), (
            "purge_user_memory must preserve the User node"
        )
        remaining = await neo4j_client.execute_read(
            "MATCH (e:Experience {id: $id}) RETURN e.id AS id", {"id": exp_id},
        )
        assert not remaining, "the derived Experience node should be gone"
