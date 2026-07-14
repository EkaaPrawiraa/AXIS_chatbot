"""shared_fixtures"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio

from agentic.memory import neo4j_client as nc



def _neo4j_reachable() -> bool:
    """import lazy"""
    try:
        from neo4j import AsyncGraphDatabase  # noqa: F401
    except Exception:
        return False

    async def _check() -> bool:
        cfg = nc.Neo4jConfig.from_env()
        try:
            client = await nc.Neo4jClient.create(cfg)
            healthy = await client.health_check()
            await client.close()
            return healthy
        except Exception:
            return False

    try:
        return asyncio.run(_check())
    except Exception:
        return False


NEO4J_OK = _neo4j_reachable()
neo4j_required = pytest.mark.skipif(
    not NEO4J_OK,
    reason=(
        "Neo4j is not reachable. Set NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD "
        "to point at a running instance, or run docker-compose up neo4j."
    ),
)


# skip error

@pytest_asyncio.fixture
async def neo4j_client() -> AsyncIterator[nc.Neo4jClient]:
    if not NEO4J_OK:
        pytest.skip("Neo4j not reachable")

    client = await nc.init_client()
    try:
        yield client
    finally:
        await nc.close_client()


# buat ns ngambil data

@pytest_asyncio.fixture
async def test_namespace(neo4j_client: nc.Neo4jClient) -> AsyncIterator[dict]:
    """set to ephemeral"""
    ns         = f"pytest-{uuid.uuid4()}"
    user_id    = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    session_id_2 = str(uuid.uuid4())

    await neo4j_client.execute_write(
        """
        CREATE (u:User {
            id:                 $user_id,
            name:               'Test User',
            display_name:       'tester',
            preferred_language: 'en',
            created_at:         datetime(),
            consent_research:   false,
            test_namespace:     $ns,
            active:             true
        })
        CREATE (s1:Session {
            id:              $session_id,
            started_at:      datetime(),
            last_activity:   datetime(),
            ended_at:        null,
            summary:         null,
            test_namespace:  $ns,
            active:          true
        })
        CREATE (s2:Session {
            id:              $session_id_2,
            started_at:      datetime() - duration('PT3H'),
            last_activity:   datetime() - duration('PT2H30M'),
            ended_at:        null,
            summary:         null,
            test_namespace:  $ns,
            active:          true
        })
        CREATE (u)-[:HAD_SESSION {
            t_valid:        datetime(),
            t_invalid:      null,
            confidence:     1.0,
            source_session: $session_id
        }]->(s1)
        CREATE (u)-[:HAD_SESSION {
            t_valid:        datetime() - duration('PT3H'),
            t_invalid:      null,
            confidence:     1.0,
            source_session: $session_id_2
        }]->(s2)
        """,
        {
            "ns":           ns,
            "user_id":      user_id,
            "session_id":   session_id,
            "session_id_2": session_id_2,
        },
    )

    try:
        yield {
            "namespace":    ns,
            "user_id":      user_id,
            "session_id":   session_id,
            "session_id_2": session_id_2,
        }
    finally:
        # tag nodes
        await neo4j_client.execute_write(
            """
            MATCH (n)
            WHERE n.test_namespace = $ns
            DETACH DELETE n
            """,
            {"ns": ns},
        )


@pytest_asyncio.fixture
async def seed_topic(neo4j_client: nc.Neo4jClient, test_namespace: dict) -> str:
    """needed."""
    ns = test_namespace["namespace"]
    topic_id = f"{ns}-topic-academic"
    await neo4j_client.execute_write(
        """
        CREATE (t:Topic {
            id:             $id,
            name:           'academic-stress',
            category:       'academic',
            created_at:     datetime(),
            test_namespace: $ns
        })
        """,
        {"id": topic_id, "ns": ns},
    )
    return topic_id
