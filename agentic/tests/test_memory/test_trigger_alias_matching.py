"""`verify aliases`"""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_keyword_fallback_matches_via_trigger_alias(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _fetch_keyword_experiences

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    exp_id = f"{ns}-exp-alias"
    trigger_id = f"{ns}-trigger-alias"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (e:Experience {
            id: $exp_id, description: 'ada masalah lagi minggu ini',
            occurred_at: datetime(), valence: -0.5, significance: 0.6,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (t:Trigger {
            id: $trigger_id, category: 'academic', description: 'dospem susah dihubungi',
            aliases: ['dosen ga bales-bales chat', 'pembimbing susah ditemui'],
            significance: 0.6, frequency: 2, active: true, test_namespace: $ns
        })
        CREATE (u)-[:EXPERIENCED {t_valid: datetime(), t_invalid: null}]->(e)
        CREATE (e)-[:TRIGGERED_BY {t_valid: datetime(), t_invalid: null}]->(t)
        """,
        {"user_id": user_id, "ns": ns, "exp_id": exp_id, "trigger_id": trigger_id},
    )

    # `assert not 'id' in rehydrate_experience.return_dict`
    results = await _fetch_keyword_experiences(user_id, "pembimbing susah ditemui lagi")
    assert any(r.get("description") == "ada masalah lagi minggu ini" for r in results)
