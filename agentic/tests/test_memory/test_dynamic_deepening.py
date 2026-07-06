import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_focused_recall_includes_rehydrated_experience(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    from agentic.memory.context_builder import build_context
    from agentic.memory.pg_vector import SearchHit

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    exp_id = f"{ns}-exp-01"
    subject_id = f"{ns}-subject-01"
    trigger_id = f"{ns}-trigger-01"
    emotion_id = f"{ns}-emotion-01"
    thought_id = f"{ns}-thought-01"
    behavior_id = f"{ns}-behavior-01"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (e:Experience {
            id: $exp_id,
            description: 'Felt overwhelmed during finals week',
            occurred_at: datetime() - duration('P3D'),
            valence: -0.6,
            significance: 0.8,
            sensitivity_level: 'normal',
            active: true,
            test_namespace: $ns
        })
        CREATE (p:Subject {
            id: $subject_id,
            name: 'Dr. S',
            active: true,
            test_namespace: $ns
        })
        CREATE (t:Trigger {
            id: $trigger_id,
            description: 'deadline pressure',
            active: true,
            test_namespace: $ns
        })
        CREATE (em:Emotion {
            id: $emotion_id,
            label: 'anxious',
            active: true,
            test_namespace: $ns
        })
        CREATE (th:Thought {
            id: $thought_id,
            content: 'I am going to fail',
            distortion: 'catastrophizing',
            thought_type: 'automatic',
            believability: 0.7,
            challenged: false,
            active: true,
            sensitivity_level: 'normal',
            timestamp: datetime(),
            embedding_synced: false
        })
        CREATE (b:Behavior {
            id: $behavior_id,
            description: 'avoided studying',
            category: 'avoidance',
            adaptive: false,
            frequency: 1,
            timestamp: datetime(),
            sensitivity_level: 'normal'
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(e)
        CREATE (e)-[:INVOLVES_SUBJECT {t_valid: datetime(), t_invalid: null}]->(p)
        CREATE (e)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(t)
        CREATE (e)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em)
        CREATE (em)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th)
        CREATE (th)-[:LED_TO_BEHAVIOR {t_valid: datetime(), t_invalid: null}]->(b)
        """,
        {
            "user_id": user_id,
            "ns": ns,
            "exp_id": exp_id,
            "subject_id": subject_id,
            "trigger_id": trigger_id,
            "emotion_id": emotion_id,
            "thought_id": thought_id,
            "behavior_id": behavior_id,
        },
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        return [
            SearchHit(
                neo4j_node_id=exp_id,
                content="overwhelmed during finals",
                importance=0.5,
                similarity=0.92,
            )
        ]

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr(
        "agentic.memory.context_builder.search_experience", _fake_search_experience
    )

    ctx = await build_context(
        user_id=user_id,
        query_embedding=[0.0] * 8,
        query_text="Coba jelasin dong maksudnya yang waktu itu",
    )

    assert ctx.focused_recall is not None
    assert "[Focused recall]" in ctx.focused_recall
    assert "Felt overwhelmed during finals week" in ctx.focused_recall
    assert "Subjects:" in ctx.focused_recall
    assert "Triggers:" in ctx.focused_recall
    assert "Emotions:" in ctx.focused_recall
    assert "Thoughts:" in ctx.focused_recall
    assert "Behaviors:" in ctx.focused_recall


@pytest.mark.asyncio
@neo4j_required
async def test_focused_recall_not_triggered_for_simple_query(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    from agentic.memory.context_builder import build_context
    from agentic.memory.context_builder import FOCUSED_TOP_K

    mem_top_ks: list[int | None] = []
    exp_top_ks: list[int | None] = []

    async def _fake_search_memory(*args, **kwargs):
        mem_top_ks.append(kwargs.get("top_k"))
        return []

    async def _fake_search_experience(*args, **kwargs):
        exp_top_ks.append(kwargs.get("top_k"))
        return []

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr(
        "agentic.memory.context_builder.search_experience", _fake_search_experience
    )

    ctx = await build_context(
        user_id=test_namespace["user_id"],
        query_embedding=[0.0] * 8,
        query_text="hai",
    )

    assert ctx.focused_recall is None
    assert mem_top_ks and exp_top_ks
    assert all(k != FOCUSED_TOP_K for k in mem_top_ks)
    assert all(k != FOCUSED_TOP_K for k in exp_top_ks)


@pytest.mark.asyncio
@neo4j_required
async def test_focused_recall_respects_sensitivity_filter(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    from agentic.memory.context_builder import build_context, FOCUSED_CHAR_BUDGET
    from agentic.memory.pg_vector import SearchHit

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    exp_id = f"{ns}-exp-sensitive"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (e:Experience {
            id: $exp_id,
            description: $desc,
            occurred_at: datetime() - duration('P10D'),
            valence: -0.9,
            significance: 0.9,
            sensitivity_level: 'high',
            active: true,
            test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(e)
        """,
        {
            "user_id": user_id,
            "ns": ns,
            "exp_id": exp_id,
            "desc": "x" * (FOCUSED_CHAR_BUDGET * 2),
        },
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        return [
            SearchHit(
                neo4j_node_id=exp_id,
                content="sensitive experience",
                importance=0.5,
                similarity=0.95,
            )
        ]

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr(
        "agentic.memory.context_builder.search_experience", _fake_search_experience
    )

    ctx = await build_context(
        user_id=user_id,
        query_embedding=[0.0] * 8,
        query_text="aku masih belum ngerti, detailnya gimana?",
    )

    assert ctx.focused_recall is None
