"""utility/synthetic_chat_eval/users/happy_user.py

Persona: Budi — 2nd-semester Computer Science student with positive outlook.
PHQ-9 baseline: 2 (minimal / flourishing).

Login:
  email    : synth_happy_budi@seed.local
  password : budi1234
  user_id  : c3d4e5f6-0003-7a8b-9c0d-1e2f3a4b5c6d
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from utility.synthetic_chat_eval._common import (
    SeedConfig,
    _iso,
    _now,
    _purge_namespace,
    _session_ids_for_namespace,
    _tag_node,
    _upsert_pg_embedding,
    _upsert_pg_user_and_sessions,
    _write_assessment_node,
)

PERSONA_CONFIG = {
    "email": "synth_happy_budi@seed.local",
    "password": "budi1234",
    "user_id": "c3d4e5f6-0003-7a8b-9c0d-1e2f3a4b5c6d",
    "name": "Budi",
    "namespace": "synth-happy-budi",
    "scenario_name": "synth_happy_budi",
    "password_hash": "$2b$12$2YI8UecOgW1/4ErcxwANCus/Q9xpJBgw3c/C6HrenXnmM9qFVHISy",
    "persona_system_prompt": (
        "Kamu adalah Budi, mahasiswa semester 2 Ilmu Komputer yang sedang menikmati masa kuliah "
        "dan punya banyak hal positif. Kamu baru saja berhasil dalam proyek pertamamu, punya "
        "lingkaran pertemanan yang solid, dan aktif di komunitas coding kampus. Kamu datang ke AXIS "
        "bukan karena masalah besar, tapi karena penasaran dan ingin berdiskusi tentang goals dan "
        "rencana ke depan. Bicaralah dengan energik dan optimistis dalam bahasa Indonesia campur "
        "Inggris sesekali. Ceritakan hal-hal yang berjalan baik, ide-ide barumu, dan diskusikan "
        "ambisi serta impianmu. Sesekali tunjukkan sedikit ketidakpastian tentang masa depan — "
        "bukan kekhawatiran besar, hanya rasa ingin tahu yang sehat."
    ),
    "scenario_description": (
        "Happy student persona with minimal PHQ-9 (2), positive experiences, strong social support, "
        "and future-oriented thinking. Tests AXIS goal-setting conversation, positive reinforcement, "
        "and engagement with flourishing users."
    ),
    "phq9_baseline": 2,
}

OPENING_MESSAGES = [
    "Halo! Aku pengen ngobrol tentang rencana ke depanku. Ada banyak hal exciting yang mau aku explore!",
    "Baru aja selesai proyek pertama aku di komunitas coding dan rasanya amazing banget. Boleh cerita nggak?",
    "Aku lagi mikirin mau ambil internship di mana musim panas ini. Ada beberapa option yang menarik.",
    "Gimana sih cara AXIS bantu kalau aku mau reflect tentang progress diri sendiri?",
    "Semester ini beneran seru! Banyak hal baru yang aku pelajari. Mau share pengalaman nih.",
]


async def seed_user(cfg: SeedConfig) -> None:
    from agentic.memory.pg_vector import embed_text, is_available as pgvector_available
    from agentic.memory.knowledge_graph.kg_writer import (
        BehaviorInput,
        EmotionInput,
        ExperienceInput,
        MemoryInput,
        SubjectInput,
        ThoughtInput,
        TriggerInput,
        TopicInput,
        link_emotion_to_thought,
        link_experience_to_emotion,
        link_experience_to_person,
        link_experience_to_trigger,
        link_session_to_memory,
        link_thought_emotion_association,
        link_to_behavior,
        link_to_topic,
        link_user_recurring_theme,
        write_behavior,
        write_emotion,
        write_experience,
        write_memory,
        write_subject,
        write_thought,
        write_topic,
        write_trigger,
    )
    from agentic.memory.neo4j_client import get_client

    pg_ok = await pgvector_available()
    print(f"  pgvector available: {'YES' if pg_ok else 'NO'}")

    now = _now()
    sids = _session_ids_for_namespace(cfg.namespace, count=3)
    s1, s2, s3 = sids["s1"], sids["s2"], sids["s3"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=60, hours=2),
            "ended_at": now - timedelta(days=60, hours=1),
            "summary": (
                "Budi cerita tentang pertama kali bergabung komunitas coding kampus dan "
                "excited dengan project pertamanya. Sangat antusias. PHQ-9 = 1 (minimal)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=30, hours=2),
            "ended_at": now - timedelta(days=30, hours=1),
            "summary": (
                "Budi berbagi keberhasilan project pertamanya yang diapresiasi komunitas "
                "dan mulai berpikir tentang internship. PHQ-9 = 2 (minimal)."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=7, hours=2),
            "ended_at": now - timedelta(days=7, hours=1),
            "summary": (
                "Budi mendiskusikan rencana internship dan goals jangka panjangnya. "
                "Sangat positif dan future-oriented. PHQ-9 = 2 (minimal)."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name = 'Budi Santoso',
            u.display_name = $display_name,
            u.preferred_language = $lang,
            u.created_at = datetime(),
            u.consent_research = false,
            u.active = true
        SET u.seed_namespace = $ns
        WITH u
        UNWIND $sessions AS s
        MERGE (sess:Session {id: s.id})
        ON CREATE SET
            sess.started_at = datetime(s.started_at),
            sess.last_activity = datetime(s.ended_at),
            sess.ended_at = datetime(s.ended_at),
            sess.summary = s.summary,
            sess.active = true
        SET sess.seed_namespace = $ns
        MERGE (u)-[:HAD_SESSION]->(sess)
        """,
        {
            "user_id": cfg.user_id,
            "display_name": PERSONA_CONFIG["scenario_name"],
            "lang": cfg.preferred_language,
            "ns": cfg.namespace,
            "sessions": [
                {
                    "id": r["id"],
                    "started_at": _iso(r["started_at"]),
                    "ended_at": _iso(r["ended_at"]),
                    "summary": r["summary"],
                }
                for r in session_rows
            ],
        },
    )
    await _upsert_pg_user_and_sessions(cfg, PERSONA_CONFIG["scenario_name"], session_rows)

    topic_defs = {
        "coding":       ("coding-projects",      "academic"),
        "community":    ("campus-community",     "social"),
        "career":       ("career-planning",      "career"),
        "growth":       ("personal-growth",      "identity"),
        "friendship":   ("positive-friendships", "social"),
        "creativity":   ("creative-exploration", "hobby"),
    }
    topic_ids: dict[str, str] = {}
    for key, (name, category) in topic_defs.items():
        tid = await write_topic(TopicInput(
            name=name,
            category=category,
            sentiment=0.0,
            user_id=cfg.user_id,
            session_id=s1,
        ))
        topic_ids[key] = tid
        await _tag_node(node_id=tid, namespace=cfg.namespace)

    people: dict[str, str] = {}
    for key, name, role, sent, quality in [
        ("andi",    "Andi",      "friend",      0.85, "supportive"),
        ("wulan",   "Wulan",     "friend",      0.80, "supportive"),
        ("pak_eko", "Pak Eko",   "professor",   0.75, "supportive"),
        ("kak_rio", "Kak Rio",   "mentor",      0.90, "supportive"),
        ("adik",    "Adik",      "sibling",     0.88, "supportive"),
    ]:
        pid = await write_subject(SubjectInput(
            name=name,
            role=role,
            sentiment=sent,
            relationship_quality=quality,
            subject_type="person",
            user_id=cfg.user_id,
            session_id=s1,
        ))
        people[key] = pid
        await _tag_node(node_id=pid, namespace=cfg.namespace)

    triggers: dict[str, str] = {}
    for key, (cat, desc, sess) in {
        "first_project":     ("achievement", "bergabung komunitas coding dan mengerjakan project pertama",            s1),
        "peer_appreciation": ("social",      "teman-teman di komunitas memberikan feedback positif untuk kodenya",   s2),
        "project_success":   ("achievement", "project pertamanya berhasil di-deploy dan dipakai anggota komunitas",  s2),
        "internship_search": ("career",      "mulai aktif mencari dan mengevaluasi internship untuk musim panas",    s3),
        "mentor_guidance":   ("social",      "Kak Rio menawarkan bimbingan informal untuk persiapan karir",         s3),
    }.items():
        embedding = await embed_text(desc)
        tid = await write_trigger(TriggerInput(
            category=cat,
            description=desc,
            user_id=cfg.user_id,
            session_id=sess,
            embedding=embedding,
        ))
        triggers[key] = tid
        await _tag_node(node_id=tid, namespace=cfg.namespace)
        await _upsert_pg_embedding(
            table="trigger_embeddings",
            user_id=cfg.user_id,
            neo4j_node_id=tid,
            content=desc,
            embedding=embedding,
            importance=0.65,
        )

    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive, sess) in {
        "daily_coding":    ("adaptive_coping", "meluangkan 2 jam setiap hari untuk coding project pribadi",    True, s1),
        "peer_collab":     ("adaptive_coping", "aktif berkolaborasi dan review kode teman di komunitas",       True, s2),
        "sharing_wins":    ("adaptive_coping", "berbagi pencapaian kecil dengan keluarga setiap minggu",       True, s2),
        "research_intern": ("adaptive_coping", "meneliti dan membandingkan 5 perusahaan internship potensial", True, s3),
        "skill_mapping":   ("adaptive_coping", "membuat roadmap skill yang perlu dikembangkan untuk karir",   True, s3),
    }.items():
        bid = await write_behavior(BehaviorInput(
            description=desc,
            category=cat,
            adaptive=adaptive,
            user_id=cfg.user_id,
            session_id=sess,
        ))
        behaviors[key] = bid
        await _tag_node(node_id=bid, namespace=cfg.namespace)

    thoughts: dict[str, str] = {}
    thought_specs = {
        "can_learn_anything": ("Selama aku mau belajar, aku bisa kuasai teknologi apapun",       "adaptive",    None,              0.80, s1),
        "collaboration_key":  ("Hasil terbaik datang dari kolaborasi, bukan kerja sendirian",    "adaptive",    None,              0.82, s2),
        "uncertainty_ok":     ("Tidak tahu semua jawaban sekarang itu normal dan justru exciting", "adaptive",  None,              0.75, s3),
        "build_to_impact":    ("Aku ingin membuat teknologi yang benar-benar membantu orang lain", "adaptive",  None,              0.85, s3),
    }
    for key, (content, ttype, dist, bel, sess) in thought_specs.items():
        embedding = await embed_text(content)
        tid = await write_thought(ThoughtInput(
            content=content,
            thought_type=ttype,
            distortion=dist,
            believability=bel,
            user_id=cfg.user_id,
            session_id=sess,
            embedding=embedding,
        ))
        thoughts[key] = tid
        await _tag_node(node_id=tid, namespace=cfg.namespace)
        await _upsert_pg_embedding(
            table="thought_embeddings",
            user_id=cfg.user_id,
            neo4j_node_id=tid,
            content=content,
            embedding=embedding,
            importance=float(bel),
        )

    async def mk_emotion(label: str, intensity: float, valence: float, text: str, sess: str) -> str:
        eid = await write_emotion(EmotionInput(
            label=label,
            intensity=intensity,
            valence=valence,
            source_text=text,
            user_id=cfg.user_id,
            session_id=sess,
        ))
        await _tag_node(node_id=eid, namespace=cfg.namespace)
        return eid

    experience_rows: list[dict[str, Any]] = [
        {
            "key": "joining_community",
            "desc": "Budi bergabung komunitas coding kampus dan langsung dapat project web app untuk manajemen jadwal komunitas.",
            "when": now - timedelta(days=61),
            "valence": 0.82,
            "significance": 0.75,
            "session": s1,
            "triggers": ["first_project"],
            "topics": ["coding", "community", "growth"],
            "people": ["andi", "pak_eko"],
            "emotions": [
                ("excited",  0.85, 0.82, "Akhirnya bisa coding sesuatu yang nyata dan berguna!"),
                ("curious",  0.78, 0.70, "Banyak hal baru yang ingin aku eksplorasi di sini."),
            ],
            "thoughts": ["can_learn_anything"],
            "behaviors": ["daily_coding"],
        },
        {
            "key": "project_deployment",
            "desc": "Project web app Budi berhasil di-deploy dan digunakan oleh seluruh anggota komunitas, mendapat applause dari seniors.",
            "when": now - timedelta(days=31),
            "valence": 0.90,
            "significance": 0.85,
            "session": s2,
            "triggers": ["project_success", "peer_appreciation"],
            "topics": ["coding", "community", "friendship"],
            "people": ["andi", "wulan", "kak_rio"],
            "emotions": [
                ("proud",     0.88, 0.85, "Melihat orang lain pakai kodenya sendiri rasanya luar biasa."),
                ("grateful",  0.82, 0.80, "Bersyukur punya teman-teman yang supportif dan percaya sama aku."),
                ("motivated", 0.86, 0.84, "Ini bikin aku makin semangat untuk buat project yang lebih besar."),
            ],
            "thoughts": ["collaboration_key", "build_to_impact"],
            "behaviors": ["peer_collab", "sharing_wins"],
        },
        {
            "key": "internship_planning",
            "desc": "Budi mulai meneliti internship dengan serius, membuat skill roadmap, dan mendapat bimbingan dari Kak Rio tentang arah karir.",
            "when": now - timedelta(days=8),
            "valence": 0.75,
            "significance": 0.78,
            "session": s3,
            "triggers": ["internship_search", "mentor_guidance"],
            "topics": ["career", "growth", "coding"],
            "people": ["kak_rio", "andi", "adik"],
            "emotions": [
                ("hopeful",     0.80, 0.78, "Ada banyak kemungkinan bagus di depan, tinggal pilih jalan yang paling sesuai."),
                ("determined",  0.82, 0.80, "Aku serius mau mempersiapkan diri sebaik mungkin."),
                ("slightly_uncertain", 0.45, -0.15, "Belum 100% yakin mana yang paling tepat, tapi itu OK."),
            ],
            "thoughts": ["uncertainty_ok", "build_to_impact"],
            "behaviors": ["research_intern", "skill_mapping"],
        },
    ]

    exp_ids: dict[str, str] = {}
    for row in experience_rows:
        embedding = await embed_text(row["desc"])
        exp_id = await write_experience(ExperienceInput(
            description=row["desc"],
            occurred_at=_iso(row["when"]),
            extracted_at=_iso(now),
            valence=row["valence"],
            significance=row["significance"],
            user_id=cfg.user_id,
            session_id=row["session"],
            embedding=embedding,
        ))
        exp_ids[row["key"]] = exp_id
        await _tag_node(node_id=exp_id, namespace=cfg.namespace)
        await _upsert_pg_embedding(
            table="experience_embeddings",
            user_id=cfg.user_id,
            neo4j_node_id=exp_id,
            content=row["desc"],
            embedding=embedding,
            importance=float(row["significance"]),
        )
        for tkey in row["triggers"]:
            await link_experience_to_trigger(exp_id, triggers[tkey], row["session"])
        for tkey in row["topics"]:
            await link_to_topic(exp_id, "Experience", topic_ids[tkey], row["session"])
        for pkey in row["people"]:
            await link_experience_to_person(exp_id, people[pkey], row["session"])

        emotion_ids = []
        for label, intensity, valence, text in row["emotions"]:
            eid = await mk_emotion(label, float(intensity), float(valence), text, row["session"])
            emotion_ids.append(eid)
            await link_experience_to_emotion(exp_id, eid, row["session"])
            await link_to_topic(eid, "Emotion", topic_ids[row["topics"][0]], row["session"])

        for tkey in row["thoughts"]:
            for eid in emotion_ids:
                await link_emotion_to_thought(eid, thoughts[tkey], row["session"])
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.78)
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=1,
        severity_label="minimal",
        item_responses={"q1": 0, "q2": 0, "q3": 0, "q4": 1, "q5": 0, "q6": 0, "q7": 0, "q8": 0, "q9": 0},
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=60, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=2,
        severity_label="minimal",
        item_responses={"q1": 0, "q2": 0, "q3": 1, "q4": 1, "q5": 0, "q6": 0, "q7": 0, "q8": 0, "q9": 0},
        delta_from_previous=1,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=30, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=2,
        severity_label="minimal",
        item_responses={"q1": 0, "q2": 0, "q3": 1, "q4": 1, "q5": 0, "q6": 0, "q7": 0, "q8": 0, "q9": 0},
        delta_from_previous=0,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=7, hours=1, minutes=20)),
        namespace=cfg.namespace,
    )

    for tkey, conf in [("coding", 0.90), ("community", 0.88), ("career", 0.85), ("growth", 0.82)]:
        await link_user_recurring_theme(cfg.user_id, topic_ids[tkey], s3, confidence=conf)

    for sess_id, summary, imp in [
        (s1, "Budi excited bergabung komunitas coding dan memulai project pertamanya. PHQ-9 = 1 (minimal).", 0.68),
        (s2, "Project Budi berhasil di-deploy dan diapresiasi komunitas. Termotivasi. PHQ-9 = 2 (minimal).", 0.78),
        (s3, "Budi aktif merencanakan internship dan karir dengan bimbingan mentor. PHQ-9 = 2 (minimal).", 0.75),
    ]:
        embedding = await embed_text(summary)
        mem_id = await write_memory(MemoryInput(
            summary=summary,
            importance=float(imp),
            user_id=cfg.user_id,
            session_id=sess_id,
            embedding=embedding,
        ))
        await _tag_node(node_id=mem_id, namespace=cfg.namespace)
        await _upsert_pg_embedding(
            table="memory_embeddings",
            user_id=cfg.user_id,
            neo4j_node_id=mem_id,
            content=summary,
            embedding=embedding,
            importance=float(imp),
        )
        await link_session_to_memory(sess_id, mem_id, sess_id)

    print(f"Seed happy_user (Budi) complete. user_id={cfg.user_id}, namespace={cfg.namespace}")
