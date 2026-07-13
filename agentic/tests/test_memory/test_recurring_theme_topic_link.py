"""RELATED_TO_TOPIC (Experience/Thought -> Topic) is written by the
finalizer (kg_extractor extracts a topic per fact, kg_writer links it) but
was never read -- only the separate HAS_RECURRING_THEME (User -> Topic) edge
was, so a recurring theme surfaced as a bare label with no link back to the
concrete experience that produced it. This verifies _fetch_themes now
cross-references back to source experiences."""

import pytest

from agentic.tests.test_memory.conftest import neo4j_required


@pytest.mark.asyncio
@neo4j_required
async def test_recurring_theme_includes_example_experiences(
    neo4j_client,
    test_namespace,
):
    from agentic.memory.context_builder import _fetch_themes

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]
    topic_id = f"{ns}-topic-thesis"
    exp_id = f"{ns}-topic-exp"

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (top:Topic {
            id: $topic_id, name: 'thesis_stress', category: 'academic',
            avg_sentiment: -0.4, test_namespace: $ns
        })
        CREATE (u)-[:HAS_RECURRING_THEME {t_valid: datetime(), t_invalid: null, times_reinforced: 3, last_reinforced: datetime()}]->(top)
        CREATE (e:Experience {
            id: $exp_id, description: 'revisi bab 3 ditolak dospem lagi',
            occurred_at: datetime(), valence: -0.6, significance: 0.7,
            sensitivity_level: 'normal', active: true, test_namespace: $ns
        })
        CREATE (e)-[:RELATED_TO_TOPIC {t_valid: datetime(), t_invalid: null}]->(top)
        """,
        {"user_id": user_id, "ns": ns, "topic_id": topic_id, "exp_id": exp_id},
    )

    themes = await _fetch_themes(user_id)
    thesis_theme = next(t for t in themes if t["topic"] == "thesis_stress")
    assert "revisi bab 3 ditolak dospem lagi" in thesis_theme["example_experiences"]
