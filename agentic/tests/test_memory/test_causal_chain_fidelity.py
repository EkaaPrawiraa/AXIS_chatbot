"""Regression: _rehydrate_experience used to bucket-collect each node type
(collect(DISTINCT trigger), collect(DISTINCT emotion), ...) before joining
them into one flat "Triggers: A, B -> Emotions: X, Y" string. When one
experience had two parallel triggers/emotions, the rendered text implied a
single causal chain even though the schema has no edge correlating which
trigger caused which emotion, and which emotion's own thought/behavior got
mixed with another emotion's. Fixed by grouping Thought/Behavior under the
Emotion that actually produced them (the one pairing the schema supports)."""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_two_emotions_keep_their_own_thought_and_behavior(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _rehydrate_experience

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    exp_id = f"{ns}-exp-multi"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (e:Experience {
            id: $exp_id, description: 'Sidang ditunda dan revisi menumpuk',
            occurred_at: datetime(), valence: -0.7, significance: 0.8,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (t1:Trigger {id: $t1, description: 'sidang ditunda', active: true, test_namespace: $ns})
        CREATE (t2:Trigger {id: $t2, description: 'revisi menumpuk', active: true, test_namespace: $ns})
        CREATE (em1:Emotion {id: $em1, label: 'cemas', active: true, test_namespace: $ns})
        CREATE (em2:Emotion {id: $em2, label: 'kecewa', active: true, test_namespace: $ns})
        CREATE (th1:Thought {
            id: $th1, content: 'aku pasti gagal sidang', distortion: 'catastrophizing',
            thought_type: 'automatic', believability: 0.8, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false
        })
        CREATE (th2:Thought {
            id: $th2, content: 'aku ketinggalan dari teman seangkatan', distortion: 'overgeneralization',
            thought_type: 'automatic', believability: 0.6, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false
        })
        CREATE (b1:Behavior {
            id: $b1, description: 'begadang ngerjain revisi', category: 'avoidance',
            adaptive: false, frequency: 1, timestamp: datetime(), sensitivity_level: 'normal'
        })
        CREATE (b2:Behavior {
            id: $b2, description: 'menghindari grup angkatan', category: 'social_withdrawal',
            adaptive: false, frequency: 1, timestamp: datetime(), sensitivity_level: 'normal'
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(e)
        CREATE (e)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(t1)
        CREATE (e)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(t2)
        CREATE (e)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em1)
        CREATE (e)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em2)
        CREATE (em1)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th1)
        CREATE (em2)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th2)
        CREATE (em1)-[:LED_TO_BEHAVIOR {t_valid: datetime(), t_invalid: null}]->(b1)
        CREATE (em2)-[:LED_TO_BEHAVIOR {t_valid: datetime(), t_invalid: null}]->(b2)
        """,
        {
            "user_id": user_id, "ns": ns, "exp_id": exp_id,
            "t1": f"{ns}-t1", "t2": f"{ns}-t2",
            "em1": f"{ns}-em1", "em2": f"{ns}-em2",
            "th1": f"{ns}-th1", "th2": f"{ns}-th2",
            "b1": f"{ns}-b1", "b2": f"{ns}-b2",
        },
    )

    rec = await _rehydrate_experience(user_id, exp_id)
    assert rec is not None

    chains = {c["label"]: c for c in rec["emotion_chains"]}
    assert set(chains.keys()) == {"cemas", "kecewa"}

    cemas_thoughts = {t["content"] for t in chains["cemas"]["thoughts"]}
    kecewa_thoughts = {t["content"] for t in chains["kecewa"]["thoughts"]}
    assert cemas_thoughts == {"aku pasti gagal sidang"}
    assert kecewa_thoughts == {"aku ketinggalan dari teman seangkatan"}

    cemas_behaviors = {b["description"] for b in chains["cemas"]["behaviors"]}
    kecewa_behaviors = {b["description"] for b in chains["kecewa"]["behaviors"]}
    assert cemas_behaviors == {"begadang ngerjain revisi"}
    assert kecewa_behaviors == {"menghindari grup angkatan"}

    # Flat backward-compat union still populated for compute_relation_richness
    # and PHQ-noise filtering, which only check truthiness/content.
    assert {e for e in rec["emotions"]} == {"cemas", "kecewa"}
    assert len(rec["thoughts"]) == 2
    assert len(rec["behaviors"]) == 2

    from agentic.memory.context_builder import _render_causal_chain

    rendered = _render_causal_chain(
        triggers=rec["triggers"], emotion_chains=rec["emotion_chains"]
    )
    # The old bug: rendering would cross-join, e.g. implying "sidang ditunda"
    # caused "kecewa" via a shared flat arrow. New rendering keeps each
    # emotion's own thought/behavior nested under it, not fused across.
    assert "cemas" in rendered and "kecewa" in rendered
    assert "aku pasti gagal sidang" in rendered
    assert "aku ketinggalan dari teman seangkatan" in rendered


@pytest.mark.asyncio
@neo4j_required
async def test_trauma_tier_keeps_emotion_label_but_strips_thought_and_behavior(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _rehydrate_experience

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    exp_id = f"{ns}-exp-trauma"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (e:Experience {
            id: $exp_id, description: 'peristiwa berat', occurred_at: datetime(),
            valence: -0.9, significance: 0.95, sensitivity_level: 'trauma',
            active: true, test_namespace: $ns
        })
        CREATE (em:Emotion {id: $em, label: 'takut', active: true, test_namespace: $ns})
        CREATE (th:Thought {
            id: $th, content: 'detail traumatis', distortion: null, thought_type: 'automatic',
            believability: 0.9, challenged: false, active: true, sensitivity_level: 'normal',
            timestamp: datetime(), embedding_synced: false
        })
        CREATE (b:Behavior {
            id: $b, description: 'detail perilaku traumatis', category: 'avoidance',
            adaptive: false, frequency: 1, timestamp: datetime(), sensitivity_level: 'normal'
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(e)
        CREATE (e)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em)
        CREATE (em)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th)
        CREATE (em)-[:LED_TO_BEHAVIOR {t_valid: datetime(), t_invalid: null}]->(b)
        """,
        {
            "user_id": user_id, "ns": ns, "exp_id": exp_id,
            "em": f"{ns}-em-trauma", "th": f"{ns}-th-trauma", "b": f"{ns}-b-trauma",
        },
    )

    rec = await _rehydrate_experience(user_id, exp_id)
    assert rec is not None
    assert rec["description"] == "[Konten trauma]"

    chains = rec["emotion_chains"]
    assert len(chains) == 1
    assert chains[0]["label"] == "takut"
    assert chains[0]["thoughts"] == []
    assert chains[0]["behaviors"] == []
