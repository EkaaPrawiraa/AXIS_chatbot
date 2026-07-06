"""
Regression test for AssessmentRepository.get_distress_snapshot's
recurring_trigger_active recency bound (AGENTIC #5).

Root cause: Trigger nodes are only ever deactivated on explicit,
LLM-detected resolution (kg_algorithm/lifecycle.py::deactivate_trigger) --
there is no time-based decay. Before this fix, the Cypher behind
recurring_trigger_active checked only `active = true` and
`frequency >= 2`, with no bound on `last_seen`. That means any trigger a
user ever mentioned twice stayed "recurring" forever, and Tier 2's
event-based PHQ-9 gate (phq9_check.py::_evaluate_tier2) treated that as
a fresh distress cluster indefinitely -- re-offering PHQ-9 every
RETRY_DAYS_FOR_DISTRESS (3) days regardless of how long ago the trigger
was actually last mentioned, defeating the intended 14-day scheduled
cadence (SCHEDULED_INTERVAL_DAYS in phq9_check.py).

The fix bounds the trigger match to `t.last_seen >= since`, the same
LOOKBACK_DAYS_FOR_KG (7-day) window already used for the session-based
distress signal, so a trigger only counts as "recurring" if it actually
reappeared recently.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio

from agentic.memory import neo4j_client as nc
from agentic.memory.assessment_repo import AssessmentRepository

from .conftest import neo4j_required

pytestmark = [pytest.mark.asyncio, neo4j_required]


@pytest_asyncio.fixture
async def raw_neo4j_driver(neo4j_client: nc.Neo4jClient):
    """
    A raw neo4j driver, matching how AssessmentRepository is actually
    constructed in production (chat_graph.py uses pg_vector.client.get_neo4j(),
    a plain AsyncGraphDatabase driver -- distinct from the Neo4jClient
    wrapper singleton used elsewhere in the KG code).
    """
    del neo4j_client  # ensures the shared client/env is already verified reachable
    from neo4j import AsyncGraphDatabase

    cfg = nc.Neo4jConfig.from_env()
    driver = AsyncGraphDatabase.driver(cfg.uri, auth=(cfg.username, cfg.password))
    try:
        yield driver
    finally:
        await driver.close()


@pytest_asyncio.fixture
async def user_with_stale_and_fresh_triggers(
    neo4j_client: nc.Neo4jClient,
) -> AsyncIterator[dict]:
    ns = f"pytest-trigger-{uuid.uuid4()}"
    user_id = f"{ns}-user"
    stale_id = f"{ns}-stale-trigger"
    fresh_id = f"{ns}-fresh-trigger"

    stale_last_seen = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    await neo4j_client.execute_write(
        """
        CREATE (u:User {id: $user_id, test_namespace: $ns})
        CREATE (stale:Trigger {
            id: $stale_id, category: 'academic', description: 'tugas kuliah',
            frequency: 4, active: true, last_seen: datetime($stale_last_seen),
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_TRIGGER {t_valid: datetime(), t_invalid: null}]->(stale)
        """,
        {
            "user_id": user_id,
            "ns": ns,
            "stale_id": stale_id,
            "stale_last_seen": stale_last_seen,
        },
    )

    try:
        yield {
            "namespace": ns,
            "user_id": user_id,
            "stale_id": stale_id,
            "fresh_id": fresh_id,
        }
    finally:
        await neo4j_client.execute_write(
            "MATCH (n) WHERE n.test_namespace = $ns DETACH DELETE n",
            {"ns": ns},
        )


class TestRecurringTriggerRecencyBound:
    async def test_stale_trigger_not_recurring(
        self,
        raw_neo4j_driver,
        user_with_stale_and_fresh_triggers: dict,
    ) -> None:
        repo = AssessmentRepository(pg_pool=None, neo4j_driver=raw_neo4j_driver)
        snapshot = await repo.get_distress_snapshot(
            user_with_stale_and_fresh_triggers["user_id"]
        )
        assert snapshot.recurring_trigger_active is False, (
            "a trigger last mentioned 30 days ago must not count as "
            "'recurring' -- it is stale, not a recent cluster"
        )

    async def test_fresh_recurring_trigger_still_detected(
        self,
        neo4j_client: nc.Neo4jClient,
        raw_neo4j_driver,
        user_with_stale_and_fresh_triggers: dict,
    ) -> None:
        fixture = user_with_stale_and_fresh_triggers
        await neo4j_client.execute_write(
            """
            MATCH (u:User {id: $user_id})
            CREATE (fresh:Trigger {
                id: $fresh_id, category: 'family', description: 'konflik keluarga',
                frequency: 3, active: true, last_seen: datetime(),
                test_namespace: $ns
            })
            CREATE (u)-[:HAS_TRIGGER {t_valid: datetime(), t_invalid: null}]->(fresh)
            """,
            {
                "user_id": fixture["user_id"],
                "fresh_id": fixture["fresh_id"],
                "ns": fixture["namespace"],
            },
        )

        repo = AssessmentRepository(pg_pool=None, neo4j_driver=raw_neo4j_driver)
        snapshot = await repo.get_distress_snapshot(fixture["user_id"])
        assert snapshot.recurring_trigger_active is True, (
            "a trigger reinforced today must still be detected as recurring"
        )
