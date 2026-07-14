import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError
import psycopg2
from neo4j import GraphDatabase

from config import CONFIG
from retrieval import embed_text

NEO4J_URI = CONFIG.neo4j_uri
NEO4J_USERNAME = CONFIG.neo4j_username
NEO4J_PASSWORD = CONFIG.neo4j_password
NEO4J_DATABASE = CONFIG.neo4j_database

ARYA_ID = "00000000-0000-0000-0000-000000000002"
BUDI_ID = "00000000-0000-0000-0000-000000000003"
BUDI_SESSION_ID = "11111111-1111-1111-1111-111111111111"

BUDI_MEMORY_ID = "m-budi-1"
BUDI_EXPERIENCE_ID = "e-budi-1"
BUDI_TRIGGER_ID = "tr-budi-1"
BUDI_SUBJECT_ID = "sub-budi-1"
BUDI_TOPIC_ID = "top-budi-1"
BUDI_EMOTION_ID = "em-budi-1"
BUDI_THOUGHT_ID = "th-budi-1"
BUDI_BEHAVIOR_ID = "b-budi-1"
BUDI_THOUGHT_RECORD_ID = "tr-rec-budi-1"
BUDI_ASSESSMENT_ID = "ass-budi-1"

BUDI_MEMORY_CONTENT = "Budi merasa sangat cemas karena ide skripsi bab 3 buntu dan dosen pembimbingnya sering menolak usulannya."
BUDI_EXPERIENCE_CONTENT = "Konsultasi skripsi dengan dosen pembimbing yang berujung penolakan draft bab 3."
BUDI_TRIGGER_CONTENT = "Bimbingan skripsi dan revisi bab 3 yang tak kunjung disetujui."
BUDI_THOUGHT_CONTENT = "Aku tidak akan pernah lulus dan dosen pembimbing membenciku karena aku bodoh."


def clean_postgres():
    print("[Postgres] Cleaning up old data...")
    conn = psycopg2.connect(CONFIG.database_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory_embeddings WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM experience_embeddings WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM thought_embeddings WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM trigger_embeddings WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    
    cur.execute("DELETE FROM assessments WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM messages WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM session_activity WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM chat_sessions WHERE user_id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    cur.execute("DELETE FROM users WHERE id IN (%s, %s)", (ARYA_ID, BUDI_ID))
    
    conn.commit()
    cur.close()
    conn.close()


def clean_neo4j():
    print("[Neo4j] Cleaning up old data...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("""
        MATCH (u:User)
        WHERE u.id IN [$arya_id, $budi_id]
        DETACH DELETE u
        """, arya_id=ARYA_ID, budi_id=BUDI_ID)
        
        session.run("""
        MATCH (n)
        WHERE n.id IN [$m_id, $e_id, $tr_id, $sub_id, $top_id, $em_id, $th_id, $b_id, $rec_id, $ass_id, $sess_id]
        DETACH DELETE n
        """, m_id=BUDI_MEMORY_ID, e_id=BUDI_EXPERIENCE_ID, tr_id=BUDI_TRIGGER_ID, 
             sub_id=BUDI_SUBJECT_ID, top_id=BUDI_TOPIC_ID, em_id=BUDI_EMOTION_ID, 
             th_id=BUDI_THOUGHT_ID, b_id=BUDI_BEHAVIOR_ID, rec_id=BUDI_THOUGHT_RECORD_ID,
             ass_id=BUDI_ASSESSMENT_ID, sess_id=BUDI_SESSION_ID)
    driver.close()


async def seed_data():
    print("Generating embeddings using Gemini...")
    texts = [BUDI_MEMORY_CONTENT, BUDI_EXPERIENCE_CONTENT, BUDI_TRIGGER_CONTENT, BUDI_THOUGHT_CONTENT]
    vectors = []
    for text in texts:
        for attempt in range(5):
            try:
                vectors.append(
                    await asyncio.to_thread(
                        embed_text,
                        text,
                        CONFIG,
                        task_type="RETRIEVAL_DOCUMENT",
                    )
                )
                break
            except HTTPError as exc:
                if exc.code != 429 or attempt == 4:
                    raise
                delay_seconds = 2 ** attempt
                print(f"Embedding rate-limited; retrying in {delay_seconds}s...")
                await asyncio.sleep(delay_seconds)
    
    mem_vec, exp_vec, trig_vec, thought_vec = vectors

    for vector in vectors:
        if len(vector) != CONFIG.embedding_dimension:
            raise RuntimeError(
                f"Seeder embedding dimension mismatch: expected "
                f"{CONFIG.embedding_dimension}, got {len(vector)}"
            )

    # Do not remove the previous fixture until every external embedding call
    # succeeded. A temporary provider failure must not leave the evaluation
    # database without its Arya and Budi fixtures.
    clean_postgres()
    clean_neo4j()

    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)

    print("[Postgres] Seeding users and vectors...")
    conn = psycopg2.connect(CONFIG.database_url)
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status, created_at) "
        "VALUES (%s, %s, %s, %s, 'id', true, 'active', %s)", 
        (ARYA_ID, "arya@test.com", "Arya", "nopassword", now)
    )
    cur.execute(
        "INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status, created_at) "
        "VALUES (%s, %s, %s, %s, 'id', true, 'active', %s)", 
        (BUDI_ID, "budi@test.com", "Budi", "nopassword", past)
    )
    
    cur.execute("INSERT INTO chat_sessions (id, user_id, started_at) VALUES (%s, %s, %s)", 
                (BUDI_SESSION_ID, BUDI_ID, past))
    
    cur.execute("""
        INSERT INTO memory_embeddings (user_id, neo4j_node_id, content, embedding, importance, created_at)
        VALUES (%s, %s, %s, %s::vector, %s, %s)
    """, (BUDI_ID, BUDI_MEMORY_ID, BUDI_MEMORY_CONTENT, mem_vec, 0.9, past))
    
    cur.execute("""
        INSERT INTO experience_embeddings (user_id, neo4j_node_id, content, embedding, importance, created_at)
        VALUES (%s, %s, %s, %s::vector, %s, %s)
    """, (BUDI_ID, BUDI_EXPERIENCE_ID, BUDI_EXPERIENCE_CONTENT, exp_vec, 0.8, past))
    
    cur.execute("""
        INSERT INTO thought_embeddings (user_id, neo4j_node_id, content, embedding, active, created_at)
        VALUES (%s, %s, %s, %s::vector, true, %s)
    """, (BUDI_ID, BUDI_THOUGHT_ID, BUDI_THOUGHT_CONTENT, thought_vec, past))
    
    cur.execute("""
        INSERT INTO trigger_embeddings (user_id, neo4j_node_id, content, embedding, active, created_at)
        VALUES (%s, %s, %s, %s::vector, true, %s)
    """, (BUDI_ID, BUDI_TRIGGER_ID, BUDI_TRIGGER_CONTENT, trig_vec, past))
    
    conn.commit()
    cur.close()
    conn.close()

    print("[Neo4j] Seeding Knowledge Graph...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("CREATE (u:User {id: $id, display_name: 'Arya', preferred_language: 'id'})", id=ARYA_ID)
        
        cypher = """
        CREATE (u:User {id: $u_id, display_name: 'Budi', preferred_language: 'id'})
        CREATE (s:Session {id: $s_id, started_at: $past_str})
        CREATE (m:Memory {id: $m_id, summary: $m_content, importance: 0.9, active: true})
        CREATE (e:Experience {id: $e_id, description: $e_content, occurred_at: $past_str, valence: -0.8, significance: 0.8})
        CREATE (tr:Trigger {id: $tr_id, category: 'Akademik', description: $tr_content})
        CREATE (sub:Subject {id: $sub_id, name: 'Dosen Pembimbing', subject_type: 'person', sentiment: -0.7})
        CREATE (top:Topic {id: $top_id, name: 'Skripsi Bab 3', category: 'Pendidikan', sentiment: -0.8})
        CREATE (em:Emotion {id: $em_id, label: 'Cemas', intensity: 8, valence: 'negative'})
        CREATE (th:Thought {id: $th_id, content: $th_content, thought_type: 'negative', distortion: 'catastrophizing'})
        CREATE (b:Behavior {id: $b_id, description: 'Menghindari membuka laptop', category: 'avoidance', adaptive: false})
        CREATE (rec:ThoughtRecord {id: $rec_id, situation: 'Ditolak saat bimbingan', emotions: 'Cemas (8)', alternative_thought: 'Revisi ini adalah bagian dari proses belajar.'})
        CREATE (ass:Assessment {id: $ass_id, type: 'PHQ-9', score: 14, severity: 'Moderate', taken_at: $past_str})
        
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
            u_id=BUDI_ID, s_id=BUDI_SESSION_ID, past_str=past.isoformat(),
            m_id=BUDI_MEMORY_ID, m_content=BUDI_MEMORY_CONTENT,
            e_id=BUDI_EXPERIENCE_ID, e_content=BUDI_EXPERIENCE_CONTENT,
            tr_id=BUDI_TRIGGER_ID, tr_content=BUDI_TRIGGER_CONTENT,
            sub_id=BUDI_SUBJECT_ID, top_id=BUDI_TOPIC_ID,
            em_id=BUDI_EMOTION_ID, th_id=BUDI_THOUGHT_ID, th_content=BUDI_THOUGHT_CONTENT,
            b_id=BUDI_BEHAVIOR_ID, rec_id=BUDI_THOUGHT_RECORD_ID, ass_id=BUDI_ASSESSMENT_ID
        )
    driver.close()
    
    print("Seeding completed successfully!")
    print(f"Arya (New User) ID : {ARYA_ID}")
    print(f"Budi (Rich Memory) ID : {BUDI_ID}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset and seed the two reserved evaluation accounts."
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required because this deletes existing data for Arya and Budi evaluation UUIDs.",
    )
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error("refusing destructive reset without --confirm-reset")
    CONFIG.validate_for(baseline=True)
    if not NEO4J_PASSWORD:
        parser.error("NEO4J_PASSWORD is required")
    asyncio.run(seed_data())
