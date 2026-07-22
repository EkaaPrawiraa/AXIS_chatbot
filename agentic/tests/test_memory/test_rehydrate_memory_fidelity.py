"""isolated emotions"""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_two_experiences_under_one_memory_keep_emotions_separate(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _rehydrate_memory

    user_id = test_namespace["user_id"]
    session_id = test_namespace["session_id"]
    ns = test_namespace["namespace"]
    mem_id = f"{ns}-mem-01"
    exp1_id = f"{ns}-mem-exp-1"
    exp2_id = f"{ns}-mem-exp-2"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        MATCH (s:Session {id: $session_id})
        CREATE (m:Memory {
            id: $mem_id, summary: 'Ringkasan sesi tentang sidang dan organisasi',
            importance: 0.7, created_at: datetime(), sensitivity_level: 'normal',
            active: true, test_namespace: $ns
        })
        CREATE (u)-[:HAS_MEMORY {t_valid: datetime(), t_invalid: null}]->(m)
        CREATE (s)-[:CONTAINS_MEMORY {t_valid: datetime(), t_invalid: null}]->(m)

        CREATE (e1:Experience {
            id: $exp1_id, description: 'sidang ditunda', occurred_at: datetime(),
            valence: -0.6, significance: 0.7, sensitivity_level: 'normal',
            active: true, test_namespace: $ns
        })
        CREATE (e2:Experience {
            id: $exp2_id, description: 'konflik organisasi', occurred_at: datetime(),
            valence: -0.5, significance: 0.6, sensitivity_level: 'normal',
            active: true, test_namespace: $ns
        })
        CREATE (s)-[:HAD_EXPERIENCE {t_valid: datetime(), t_invalid: null}]->(e1)
        CREATE (s)-[:HAD_EXPERIENCE {t_valid: datetime(), t_invalid: null}]->(e2)

        CREATE (em1:Emotion {id: $em1, label: 'cemas', active: true, test_namespace: $ns})
        CREATE (em2:Emotion {id: $em2, label: 'lelah', active: true, test_namespace: $ns})
        CREATE (th1:Thought {
            id: $th1, content: 'aku pasti gagal sidang', distortion: 'catastrophizing',
            thought_type: 'automatic', believability: 0.7, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false
        })
        CREATE (th2:Thought {
            id: $th2, content: 'aku capek urus organisasi', distortion: null,
            thought_type: 'automatic', believability: 0.5, challenged: false,
            active: true, sensitivity_level: 'normal', timestamp: datetime(), embedding_synced: false
        })
        CREATE (e1)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em1)
        CREATE (e2)-[:TRIGGERED_EMOTION {t_valid: datetime(), t_invalid: null}]->(em2)
        CREATE (em1)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th1)
        CREATE (em2)-[:ACTIVATED_THOUGHT {t_valid: datetime(), t_invalid: null}]->(th2)
        """,
        {
            "user_id": user_id, "session_id": session_id, "ns": ns,
            "mem_id": mem_id, "exp1_id": exp1_id, "exp2_id": exp2_id,
            "em1": f"{ns}-mem-em1", "em2": f"{ns}-mem-em2",
            "th1": f"{ns}-mem-th1", "th2": f"{ns}-mem-th2",
        },
    )

    rec = await _rehydrate_memory(user_id, mem_id)
    assert rec is not None

    chains = {c["label"]: c for c in rec["emotion_chains"]}
    assert set(chains.keys()) == {"cemas", "lelah"}

    cemas_thoughts = {t["content"] for t in chains["cemas"]["thoughts"]}
    lelah_thoughts = {t["content"] for t in chains["lelah"]["thoughts"]}
    assert cemas_thoughts == {"aku pasti gagal sidang"}
    assert lelah_thoughts == {"aku capek urus organisasi"}

    assert set(rec["experiences"]) == {"sidang ditunda", "konflik organisasi"}
