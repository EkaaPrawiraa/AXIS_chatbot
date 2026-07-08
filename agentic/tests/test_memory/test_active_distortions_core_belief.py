"""prioritize core_belief"""
from __future__ import annotations

import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio

from agentic.memory import neo4j_client as nc
from agentic.memory.context_builder import _fetch_active_distortions

from .conftest import neo4j_required

pytestmark = [pytest.mark.asyncio, neo4j_required]


@pytest_asyncio.fixture
async def user_with_mixed_thoughts(neo4j_client: nc.Neo4jClient) -> AsyncIterator[dict]:
    ns = f"pytest-corebelief-{uuid.uuid4()}"
    user_id = f"{ns}-user"

    await neo4j_client.execute_write(
        """
        CREATE (u:User {id: $user_id, test_namespace: $ns})
        CREATE (core:Thought {
            id: $core_id, content: 'aku selalu jadi beban buat orang lain',
            thought_type: 'core_belief', distortion: null, believability: 0.8,
            challenged: false, active: true, sensitivity_level: 'normal',
            timestamp: datetime() - duration('P30D'), test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT]->(core)
        CREATE (automatic:Thought {
            id: $automatic_id, content: 'ujian ini pasti bakal gagal total',
            thought_type: 'automatic', distortion: 'catastrophizing',
            believability: 0.6, challenged: false, active: true,
            sensitivity_level: 'normal', timestamp: datetime(),
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT]->(automatic)
        CREATE (challenged_core:Thought {
            id: $challenged_id, content: 'harus jadi sempurna atau gagal',
            thought_type: 'core_belief', distortion: null, believability: 0.7,
            challenged: true, active: true, sensitivity_level: 'normal',
            timestamp: datetime(), test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT]->(challenged_core)
        CREATE (inactive_core:Thought {
            id: $inactive_id, content: 'superseded core belief',
            thought_type: 'core_belief', distortion: null, believability: 0.7,
            challenged: false, active: false, sensitivity_level: 'normal',
            timestamp: datetime(), test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT]->(inactive_core)
        """,
        {
            "user_id": user_id,
            "ns": ns,
            "core_id": f"{ns}-core",
            "automatic_id": f"{ns}-automatic",
            "challenged_id": f"{ns}-challenged",
            "inactive_id": f"{ns}-inactive",
        },
    )

    try:
        yield {"namespace": ns, "user_id": user_id}
    finally:
        await neo4j_client.execute_write(
            "MATCH (n) WHERE n.test_namespace = $ns DETACH DELETE n",
            {"ns": ns},
        )


class TestFetchActiveDistortionsCoreBeliefPriority:
    async def test_undistorted_core_belief_is_surfaced(
        self, user_with_mixed_thoughts: dict,
    ) -> None:
        rows = await _fetch_active_distortions(user_with_mixed_thoughts["user_id"])
        contents = [r["content"] for r in rows]
        assert "aku selalu jadi beban buat orang lain" in contents

    async def test_core_belief_ranked_ahead_of_more_recent_distortion(
        self, user_with_mixed_thoughts: dict,
    ) -> None:
        rows = await _fetch_active_distortions(user_with_mixed_thoughts["user_id"])
        assert rows, "expected at least one row"
        assert rows[0]["thought_type"] == "core_belief"
        assert rows[0]["content"] == "aku selalu jadi beban buat orang lain"

    async def test_challenged_core_belief_excluded(
        self, user_with_mixed_thoughts: dict,
    ) -> None:
        rows = await _fetch_active_distortions(user_with_mixed_thoughts["user_id"])
        contents = [r["content"] for r in rows]
        assert "harus jadi sempurna atau gagal" not in contents

    async def test_inactive_core_belief_excluded(
        self, user_with_mixed_thoughts: dict,
    ) -> None:
        rows = await _fetch_active_distortions(user_with_mixed_thoughts["user_id"])
        contents = [r["content"] for r in rows]
        assert "superseded core belief" not in contents
