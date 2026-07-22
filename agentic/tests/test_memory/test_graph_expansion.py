"""Task 4: candidate discovery in build_context() is pgvector-primary by design (Neo4j Community
has no native vector index); Neo4j traversal only decorated nodes vector search already found.
This verifies the bounded graph-native expansion step: a real graph hop from the vector-selected
seed to a sibling sharing the same Trigger surfaces a memory with zero embedding similarity to the
seed -- what a pure semantic-search baseline structurally cannot find (Collins & Loftus 1975,
spreading activation)."""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_sibling_experience_via_shared_trigger_surfaces_via_graph_expansion(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    from agentic.memory.context_builder import build_context
    from agentic.memory.pg_vector import SearchHit

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    seed_id = f"{ns}-seed-exp"
    sibling_id = f"{ns}-sibling-exp"
    trigger_id = f"{ns}-shared-trigger"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (trig:Trigger {
            id: $trigger_id, category: 'academic', description: 'dospem susah dihubungi',
            significance: 0.6, frequency: 2, active: true, test_namespace: $ns
        })
        CREATE (seed:Experience {
            id: $seed_id, description: 'nunggu balesan chat dospem dari kemarin',
            occurred_at: datetime(), valence: -0.5, significance: 0.7,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (sibling:Experience {
            id: $sibling_id,
            description: 'liburan kemarin ke pantai sama temen kosan seru banget rasanya lega',
            occurred_at: datetime() - duration('P5D'), valence: 0.6, significance: 0.65,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(seed)
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(sibling)
        CREATE (seed)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(trig)
        CREATE (sibling)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(trig)
        """,
        {
            "user_id": user_id, "ns": ns,
            "seed_id": seed_id, "sibling_id": sibling_id, "trigger_id": trigger_id,
        },
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        # Only the seed is "found" by vector search; the sibling shares no words/topic and is never returned here -- simulates a semantic-only baseline's miss
        return [
            SearchHit(
                neo4j_node_id=seed_id,
                content="nunggu balesan chat dospem",
                importance=0.7,
                similarity=0.9,
            )
        ]

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr("agentic.memory.context_builder.search_experience", _fake_search_experience)

    ctx = await build_context(
        user_id=user_id,
        query_embedding=[0.0] * 8,
        query_text="kok dospem belum bales-bales ya chat aku",
    )

    assert ctx.focused_recall is not None
    assert "nunggu balesan chat dospem dari kemarin" in ctx.focused_recall
    # The sibling never matched the query semantically or lexically -- it only surfaces via shared Trigger node identity
    assert "liburan kemarin ke pantai" in ctx.focused_recall

    expansion_candidates = [
        c for c in ctx.retrieval_context_dict.get("focused_recall", [])
        if c.get("source_signal") == "graph_expansion"
    ]
    assert any(c.get("id") == sibling_id for c in expansion_candidates)


@pytest.mark.asyncio
@neo4j_required
async def test_no_expansion_when_no_shared_trigger_or_subject(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    """Guards against over-eager expansion: an unrelated experience with no shared Trigger/Subject must never be pulled in."""
    from agentic.memory.context_builder import build_context
    from agentic.memory.pg_vector import SearchHit

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    seed_id = f"{ns}-seed-lonely"
    unrelated_id = f"{ns}-unrelated-exp"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (seed:Experience {
            id: $seed_id, description: 'presentasi tugas kelompok lancar',
            occurred_at: datetime(), valence: 0.3, significance: 0.6,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (unrelated:Experience {
            id: $unrelated_id, description: 'beli kucing baru minggu lalu',
            occurred_at: datetime(), valence: 0.5, significance: 0.6,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(seed)
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(unrelated)
        """,
        {"user_id": user_id, "ns": ns, "seed_id": seed_id, "unrelated_id": unrelated_id},
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        return [
            SearchHit(
                neo4j_node_id=seed_id,
                content="presentasi tugas kelompok",
                importance=0.6,
                similarity=0.9,
            )
        ]

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr("agentic.memory.context_builder.search_experience", _fake_search_experience)

    ctx = await build_context(
        user_id=user_id, query_embedding=[0.0] * 8, query_text="gimana tugas kelompok kemarin"
    )

    assert ctx.focused_recall is not None
    assert "beli kucing baru minggu lalu" not in ctx.focused_recall
