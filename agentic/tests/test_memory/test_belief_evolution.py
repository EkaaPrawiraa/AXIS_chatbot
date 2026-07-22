"""supercedes, reappears, replaced"""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_surfaces_all_three_lifecycle_edge_types(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _fetch_belief_evolution

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})

        CREATE (old_th:Thought {
            id: $old_th, content: 'aku pasti gagal sidang', distortion: 'catastrophizing',
            thought_type: 'automatic', believability: 0.8, challenged: true,
            active: false, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false,
            test_namespace: $ns
        })
        CREATE (new_th:Thought {
            id: $new_th, content: 'aku sudah siapkan revisi sebaik mungkin', distortion: null,
            thought_type: 'automatic', believability: 0.6, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false,
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT {t_valid: datetime(), t_invalid: null}]->(new_th)
        CREATE (new_th)-[:SUPERSEDES {at: datetime(), reason: 'user_reframe'}]->(old_th)

        CREATE (old_exp:Experience {
            id: $old_exp, description: 'ditolak organisasi', occurred_at: datetime(),
            valence: -0.7, significance: 0.7, sensitivity_level: 'normal', active: false,
            test_namespace: $ns
        })
        CREATE (new_exp:Experience {
            id: $new_exp, description: 'ditolak organisasi tapi jadi belajar dari feedback',
            occurred_at: datetime(), valence: 0.2, significance: 0.6,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(old_exp)
        CREATE (old_exp)-[:REAPPRAISED_AS {t_valid: datetime(), t_invalid: null, reason: 'meaning_update'}]->(new_exp)

        CREATE (old_beh:Behavior {
            id: $old_beh, description: 'begadang tiap malam', category: 'avoidance',
            adaptive: false, frequency: 3, timestamp: datetime(), sensitivity_level: 'normal',
            active: false, test_namespace: $ns
        })
        CREATE (new_beh:Behavior {
            id: $new_beh, description: 'jadwal tidur lebih teratur', category: 'self_care',
            adaptive: true, frequency: 1, timestamp: datetime(), sensitivity_level: 'normal',
            active: true, test_namespace: $ns
        })
        CREATE (u)-[:EXHIBITED {t_valid: datetime(), t_invalid: null}]->(old_beh)
        CREATE (old_beh)-[:REPLACED_BY {t_valid: datetime(), t_invalid: null, reason: 'healthier_coping'}]->(new_beh)
        """,
        {
            "user_id": user_id, "ns": ns,
            "old_th": f"{ns}-old-th", "new_th": f"{ns}-new-th",
            "old_exp": f"{ns}-old-exp", "new_exp": f"{ns}-new-exp",
            "old_beh": f"{ns}-old-beh", "new_beh": f"{ns}-new-beh",
        },
    )

    results = await _fetch_belief_evolution(user_id)
    kinds = {r["kind"] for r in results}
    assert kinds == {"thought", "experience", "behavior"}

    by_kind = {r["kind"]: r for r in results}
    assert by_kind["thought"]["old_content"] == "aku pasti gagal sidang"
    assert by_kind["thought"]["new_content"] == "aku sudah siapkan revisi sebaik mungkin"
    assert by_kind["experience"]["old_content"] == "ditolak organisasi"
    assert by_kind["experience"]["new_content"] == "ditolak organisasi tapi jadi belajar dari feedback"
    assert by_kind["behavior"]["old_content"] == "begadang tiap malam"
    assert by_kind["behavior"]["new_content"] == "jadwal tidur lebih teratur"


@pytest.mark.asyncio
@neo4j_required
async def test_trauma_tier_pair_excluded_from_ambient_signal(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _fetch_belief_evolution

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (old_exp:Experience {
            id: $old_exp, description: 'peristiwa traumatis lama', occurred_at: datetime(),
            valence: -0.9, significance: 0.95, sensitivity_level: 'trauma', active: false,
            test_namespace: $ns
        })
        CREATE (new_exp:Experience {
            id: $new_exp, description: 'sudah mulai bisa memaknai ulang', occurred_at: datetime(),
            valence: 0.1, significance: 0.6, sensitivity_level: 'normal', active: true,
            test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(old_exp)
        CREATE (old_exp)-[:REAPPRAISED_AS {t_valid: datetime(), t_invalid: null, reason: 'meaning_update'}]->(new_exp)
        """,
        {"user_id": user_id, "ns": ns, "old_exp": f"{ns}-trauma-old", "new_exp": f"{ns}-trauma-new"},
    )

    results = await _fetch_belief_evolution(user_id)
    assert not any(r["kind"] == "experience" for r in results)


@pytest.mark.asyncio
@neo4j_required
async def test_renders_as_belief_evolution_section(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    from agentic.memory.context_builder import build_context
    from agentic.memory.pg_vector import SearchHit

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (old_th:Thought {
            id: $old_th, content: 'aku ga akan pernah lulus tepat waktu', distortion: 'catastrophizing',
            thought_type: 'automatic', believability: 0.7, challenged: true,
            active: false, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false,
            test_namespace: $ns
        })
        CREATE (new_th:Thought {
            id: $new_th, content: 'progres skripsiku pelan tapi jalan', distortion: null,
            thought_type: 'automatic', believability: 0.5, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false,
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT {t_valid: datetime(), t_invalid: null}]->(new_th)
        CREATE (new_th)-[:SUPERSEDES {at: datetime(), reason: 'user_reframe'}]->(old_th)
        """,
        {"user_id": user_id, "ns": ns, "old_th": f"{ns}-render-old-th", "new_th": f"{ns}-render-new-th"},
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        return []

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr("agentic.memory.context_builder.search_experience", _fake_search_experience)

    ctx = await build_context(user_id=user_id, query_embedding=[0.0] * 8, query_text="gimana kabarku ya")
    block = ctx.as_prompt_block()

    assert "[Belief evolution]" in block
    assert "aku ga akan pernah lulus tepat waktu" in block
    assert "progres skripsiku pelan tapi jalan" in block
    assert "user_reframe" in block
