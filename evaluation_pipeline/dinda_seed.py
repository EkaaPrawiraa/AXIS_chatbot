"""Seed a second rich-memory persona (Dinda) for the EPITOME ablation
replication check: same 'rich_memory' shape as Budi (memory/experience/
trigger/subject/topic/emotion/thought/behavior graph), but a different
domain (family financial/health pressure instead of thesis supervision)
so the replication is an independent scenario, not a reworded copy.

Scoped only to Dinda's UUID -- never touches Arya or Budi's seeded data.
"""

import argparse
import asyncio
from datetime import datetime, timezone, timedelta

import psycopg2
from neo4j import GraphDatabase

from config import CONFIG
from retrieval import embed_text

DINDA_ID = "00000000-0000-0000-0000-000000000005"
DINDA_SESSION_ID = "22222222-2222-2222-2222-222222222222"

DINDA_MEMORY_ID = "m-dinda-1"
DINDA_EXPERIENCE_ID = "e-dinda-1"
DINDA_TRIGGER_ID = "tr-dinda-1"
DINDA_SUBJECT_ID = "sub-dinda-1"
DINDA_TOPIC_ID = "top-dinda-1"
DINDA_EMOTION_ID = "em-dinda-1"
DINDA_THOUGHT_ID = "th-dinda-1"
DINDA_BEHAVIOR_ID = "b-dinda-1"
DINDA_THOUGHT_RECORD_ID = "tr-rec-dinda-1"
DINDA_ASSESSMENT_ID = "ass-dinda-1"

DINDA_MEMORY_CONTENT = "Dinda merasa sangat tertekan karena ibunya sakit dan butuh biaya pengobatan tambahan, sementara penghasilan kerja part-time-nya belum cukup untuk membantu."
DINDA_EXPERIENCE_CONTENT = "Menerima telepon dari ayah bahwa kondisi ibu memburuk dan rumah sakit meminta tambahan biaya rawat inap."
DINDA_TRIGGER_CONTENT = "Telepon dari keluarga soal kondisi kesehatan ibu dan kebutuhan biaya rawat inap."
DINDA_THOUGHT_CONTENT = "Aku nggak akan pernah bisa bantu cukup dan aku gagal jadi anak yang bisa diandalkan keluarga."


def clean_postgres():
    conn = psycopg2.connect(CONFIG.database_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory_embeddings WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM experience_embeddings WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM thought_embeddings WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM trigger_embeddings WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM assessments WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM messages WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM session_activity WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM chat_sessions WHERE user_id = %s", (DINDA_ID,))
    cur.execute("DELETE FROM users WHERE id = %s", (DINDA_ID,))
    conn.commit()
    cur.close()
    conn.close()


def clean_neo4j():
    driver = GraphDatabase.driver(CONFIG.neo4j_uri, auth=(CONFIG.neo4j_username, CONFIG.neo4j_password))
    with driver.session(database=CONFIG.neo4j_database) as session:
        session.run("MATCH (u:User {id: $id}) DETACH DELETE u", id=DINDA_ID)
        session.run(
            """
            MATCH (n)
            WHERE n.id IN [$m_id, $e_id, $tr_id, $sub_id, $top_id, $em_id, $th_id, $b_id, $rec_id, $ass_id, $sess_id]
            DETACH DELETE n
            """,
            m_id=DINDA_MEMORY_ID, e_id=DINDA_EXPERIENCE_ID, tr_id=DINDA_TRIGGER_ID,
            sub_id=DINDA_SUBJECT_ID, top_id=DINDA_TOPIC_ID, em_id=DINDA_EMOTION_ID,
            th_id=DINDA_THOUGHT_ID, b_id=DINDA_BEHAVIOR_ID, rec_id=DINDA_THOUGHT_RECORD_ID,
            ass_id=DINDA_ASSESSMENT_ID, sess_id=DINDA_SESSION_ID,
        )
    driver.close()


async def seed_data():
    texts = [DINDA_MEMORY_CONTENT, DINDA_EXPERIENCE_CONTENT, DINDA_TRIGGER_CONTENT, DINDA_THOUGHT_CONTENT]
    vectors = [
        await asyncio.to_thread(embed_text, text, CONFIG, task_type="RETRIEVAL_DOCUMENT")
        for text in texts
    ]
    mem_vec, exp_vec, trig_vec, thought_vec = vectors
    for vector in vectors:
        if len(vector) != CONFIG.embedding_dimension:
            raise RuntimeError(
                f"Seeder embedding dimension mismatch: expected {CONFIG.embedding_dimension}, got {len(vector)}"
            )

    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)

    conn = psycopg2.connect(CONFIG.database_url)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status, created_at) "
        "VALUES (%s, %s, %s, %s, 'id', true, 'active', %s)",
        (DINDA_ID, "dinda@test.com", "Dinda", "nopassword", past),
    )
    cur.execute("INSERT INTO chat_sessions (id, user_id, started_at) VALUES (%s, %s, %s)", (DINDA_SESSION_ID, DINDA_ID, past))
    cur.execute(
        "INSERT INTO memory_embeddings (user_id, neo4j_node_id, content, embedding, importance, created_at) "
        "VALUES (%s, %s, %s, %s::vector, %s, %s)",
        (DINDA_ID, DINDA_MEMORY_ID, DINDA_MEMORY_CONTENT, mem_vec, 0.9, past),
    )
    cur.execute(
        "INSERT INTO experience_embeddings (user_id, neo4j_node_id, content, embedding, importance, created_at) "
        "VALUES (%s, %s, %s, %s::vector, %s, %s)",
        (DINDA_ID, DINDA_EXPERIENCE_ID, DINDA_EXPERIENCE_CONTENT, exp_vec, 0.8, past),
    )
    cur.execute(
        "INSERT INTO thought_embeddings (user_id, neo4j_node_id, content, embedding, active, created_at) "
        "VALUES (%s, %s, %s, %s::vector, true, %s)",
        (DINDA_ID, DINDA_THOUGHT_ID, DINDA_THOUGHT_CONTENT, thought_vec, past),
    )
    cur.execute(
        "INSERT INTO trigger_embeddings (user_id, neo4j_node_id, content, embedding, active, created_at) "
        "VALUES (%s, %s, %s, %s::vector, true, %s)",
        (DINDA_ID, DINDA_TRIGGER_ID, DINDA_TRIGGER_CONTENT, trig_vec, past),
    )
    conn.commit()
    cur.close()
    conn.close()

    driver = GraphDatabase.driver(CONFIG.neo4j_uri, auth=(CONFIG.neo4j_username, CONFIG.neo4j_password))
    with driver.session(database=CONFIG.neo4j_database) as session:
        cypher = """
        CREATE (u:User {id: $u_id, display_name: 'Dinda', preferred_language: 'id'})
        CREATE (s:Session {id: $s_id, started_at: $past_str})
        CREATE (m:Memory {id: $m_id, summary: $m_content, importance: 0.9, active: true})
        CREATE (e:Experience {id: $e_id, description: $e_content, occurred_at: $past_str, valence: -0.8, significance: 0.8})
        CREATE (tr:Trigger {id: $tr_id, category: 'Keluarga', description: $tr_content})
        CREATE (sub:Subject {id: $sub_id, name: 'Ayah', subject_type: 'person', sentiment: 0.3})
        CREATE (top:Topic {id: $top_id, name: 'Biaya Pengobatan Ibu', category: 'Keluarga', sentiment: -0.8})
        CREATE (em:Emotion {id: $em_id, label: 'Cemas', intensity: 8, valence: 'negative'})
        CREATE (th:Thought {id: $th_id, content: $th_content, thought_type: 'negative', distortion: 'overgeneralization'})
        CREATE (b:Behavior {id: $b_id, description: 'Menghindari membahas keuangan dengan keluarga', category: 'avoidance', adaptive: false})
        CREATE (rec:ThoughtRecord {id: $rec_id, situation: 'Telepon soal tambahan biaya rawat inap ibu', emotions: 'Cemas (8)', alternative_thought: 'Membantu keluarga tidak harus berarti menanggung semuanya sendirian.'})
        CREATE (ass:Assessment {id: $ass_id, type: 'PHQ-9', score: 12, severity: 'Moderate', taken_at: $past_str})

        CREATE (u)-[:HAD_SESSION]->(s)
        CREATE (u)-[:HAS_MEMORY]->(m)
        CREATE (u)-[:HAS_THOUGHT_RECORD]->(rec)
        CREATE (u)-[:COMPLETED_ASSESSMENT]->(ass)

        CREATE (s)-[:HAD_EXPERIENCE]->(e)
        CREATE (s)-[:CONTAINS_MEMORY]->(m)
        CREATE (s)-[:RECORDED_EMOTION]->(em)

        CREATE (e)-[:TRIGGERED_BY]->(tr)
        CREATE (e)-[:INVOLVES_SUBJECT]->(sub)
        CREATE (e)-[:RELATED_TO_TOPIC]->(top)
        CREATE (e)-[:TRIGGERED_EMOTION]->(em)

        CREATE (em)-[:ACTIVATED_THOUGHT]->(th)
        CREATE (em)-[:LED_TO_BEHAVIOR]->(b)

        CREATE (th)-[:LED_TO_BEHAVIOR]->(b)
        """
        session.run(
            cypher,
            u_id=DINDA_ID, s_id=DINDA_SESSION_ID, past_str=past.isoformat(),
            m_id=DINDA_MEMORY_ID, m_content=DINDA_MEMORY_CONTENT,
            e_id=DINDA_EXPERIENCE_ID, e_content=DINDA_EXPERIENCE_CONTENT,
            tr_id=DINDA_TRIGGER_ID, tr_content=DINDA_TRIGGER_CONTENT,
            sub_id=DINDA_SUBJECT_ID, top_id=DINDA_TOPIC_ID,
            em_id=DINDA_EMOTION_ID, th_id=DINDA_THOUGHT_ID, th_content=DINDA_THOUGHT_CONTENT,
            b_id=DINDA_BEHAVIOR_ID, rec_id=DINDA_THOUGHT_RECORD_ID, ass_id=DINDA_ASSESSMENT_ID,
        )
    driver.close()
    print(f"Dinda (Rich Memory, replication persona) ID : {DINDA_ID}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Dinda replication persona.")
    parser.add_argument("--confirm-reset", action="store_true", required=True)
    args = parser.parse_args()
    CONFIG.validate_for(baseline=True)
    if not CONFIG.neo4j_password:
        parser.error("NEO4J_PASSWORD is required")
    clean_postgres()
    clean_neo4j()
    asyncio.run(seed_data())
