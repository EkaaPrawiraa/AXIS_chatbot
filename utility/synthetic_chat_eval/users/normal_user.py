"""utility/synthetic_chat_eval/users/normal_user.py

Persona: Sari — 4th-semester Psychology student with mild daily stress.
PHQ-9 baseline: 6 (mild).

Login:
  email    : synth_normal_sari@seed.local
  password : sari1234
  user_id  : b2c3d4e5-0002-6f7a-8b9c-0d1e2f3a4b5c
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
    "email": "synth_normal_sari@seed.local",
    "password": "sari1234",
    "user_id": "b2c3d4e5-0002-6f7a-8b9c-0d1e2f3a4b5c",
    "name": "Sari",
    "namespace": "synth-normal-sari",
    "scenario_name": "synth_normal_sari",
    "password_hash": "$2b$12$2YI8UecOgW1/4ErcxwANCus/Q9xpJBgw3c/C6HrenXnmM9qFVHISy",
    "persona_system_prompt": (
        "Kamu adalah Sari, mahasiswi semester 4 Psikologi yang memiliki kehidupan cukup seimbang "
        "tapi sesekali kewalahan dengan tugas kuliah dan dinamika pertemanan. Kamu cukup self-aware "
        "dan suka merefleksikan perasaanmu. Kamu tidak sedang dalam krisis, tapi ada beberapa hal "
        "yang ingin kamu bicarakan — tekanan UTS yang datang, sedikit konflik dengan teman, dan "
        "kerinduan dengan keluarga di kampung. Bicaralah dalam bahasa Indonesia yang santai dan "
        "reflektif. Kamu terbuka tapi tidak over-share. Sesekali tunjukkan rasa penasaran tentang "
        "cara AXIS merespons, karena kamu mempelajari psikologi."
    ),
    "scenario_description": (
        "Normal student persona with mild PHQ-9 (6), manageable daily stressors, "
        "healthy coping mostly intact. Tests AXIS supportive conversation and "
        "psychoeducation delivery for non-crisis users."
    ),
    "phq9_baseline": 6,
}

OPENING_MESSAGES = [
    "Halo! Aku lagi pengen ngobrol aja sebenernya. Lagi agak banyak pikiran belakangan ini.",
    "Minggu ini lumayan padat sih — UTS, tugas kelompok yang ribet, dan aku juga lagi kangen rumah.",
    "Boleh aku cerita tentang situasi sama teman? Rasanya agak awkward mau ngomong langsung ke orangnya.",
    "Aku penasaran sebenernya, gimana cara kamu bisa bantu aku sort out perasaan-perasaan ini?",
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
            "started_at": now - timedelta(days=45, hours=2),
            "ended_at": now - timedelta(days=45, hours=1),
            "summary": (
                "Sari cerita tentang kekhawatirannya memasuki semester baru dan beradaptasi "
                "dengan kelompok studi baru. Secara umum positif tapi ada kecemasan ringan. PHQ-9 = 4 (minimal)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=21, hours=2),
            "ended_at": now - timedelta(days=21, hours=1),
            "summary": (
                "Sari membicarakan konflik kecil dengan teman sekelompok yang tidak berkontribusi. "
                "Merasa frustrasi tapi berhasil mengatasinya dengan komunikasi langsung. PHQ-9 = 5 (minimal)."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=7, hours=2),
            "ended_at": now - timedelta(days=7, hours=1),
            "summary": (
                "Sari merasa sedikit kewalahan menjelang UTS dan kangen keluarga di kampung. "
                "Tidur tidak teratur. PHQ-9 = 6 (mild)."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name = 'Sari Indah Pertiwi',
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
        "academic":    ("exam-pressure",         "academic"),
        "friendship":  ("peer-conflict",         "social"),
        "family":      ("homesickness",          "family"),
        "self_growth": ("self-reflection",       "identity"),
        "sleep":       ("irregular-sleep",       "health"),
        "balance":     ("work-life-balance",     "lifestyle"),
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
        ("maya",     "Maya",      "friend",     0.70, "supportive"),
        ("dimas",    "Dimas",     "friend",    -0.20, "complicated"),
        ("bu_ani",   "Bu Ani",    "professor",  0.55, "supportive"),
        ("mama",     "Mama",      "parent",     0.85, "supportive"),
        ("papa",     "Papa",      "parent",     0.75, "supportive"),
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
        "new_semester":    ("academic",  "mulai semester baru dengan kelompok studi yang belum dikenal",          s1),
        "group_conflict":  ("social",    "anggota kelompok tugas tidak mengerjakan bagiannya",                   s2),
        "uts_approaching": ("academic",  "UTS semakin dekat dan materi terasa menumpuk",                        s3),
        "homesick":        ("family",    "sudah 3 bulan tidak pulang ke kampung dan kangen keluarga",            s3),
        "sleep_irregular": ("health",    "tidur tidak teratur karena begadang belajar menjelang UTS",            s3),
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
            importance=0.55,
        )

    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive, sess) in {
        "journaling":     ("adaptive_coping", "menulis jurnal refleksi harian",                             True,  s1),
        "direct_talk":    ("adaptive_coping", "berbicara langsung dengan Dimas tentang pembagian tugas",    True,  s2),
        "late_study":     ("avoidance",       "belajar sampai larut malam sebelum UTS",                    False, s3),
        "video_call":     ("adaptive_coping", "video call dengan Mama dan Papa seminggu sekali",           True,  s3),
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
        "need_to_prove":   ("Aku perlu membuktikan diri di kelompok baru ini supaya diterima",    "automatic",   "should_statements", 0.55, s1),
        "unfair_blame":    ("Tidak adil kalau aku harus kerja lebih karena orang lain malas",     "automatic",   "fortune_telling",   0.60, s2),
        "enough_to_fail":  ("Kalau aku tidak belajar cukup keras, aku pasti gagal UTS",           "automatic",   "catastrophizing",   0.65, s3),
        "can_handle_this": ("Aku sudah pernah menghadapi tekanan sebelumnya dan berhasil",        "adaptive",    None,                0.72, s3),
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
            "key": "new_group_anxiety",
            "desc": "Sari bergabung dengan kelompok studi baru dan merasa perlu membuktikan diri, tapi juga excited dengan koneksi baru.",
            "when": now - timedelta(days=46),
            "valence": 0.15,
            "significance": 0.55,
            "session": s1,
            "triggers": ["new_semester"],
            "topics": ["academic", "friendship", "self_growth"],
            "people": ["maya", "bu_ani"],
            "emotions": [
                ("anxious",   0.55, -0.45, "Belum tahu ekspektasi kelompok ini."),
                ("hopeful",   0.65,  0.60, "Tapi aku excited ketemu orang-orang baru."),
            ],
            "thoughts": ["need_to_prove"],
            "behaviors": ["journaling"],
        },
        {
            "key": "group_conflict_resolution",
            "desc": "Dimas tidak mengerjakan bagiannya dalam tugas kelompok, Sari memilih berbicara langsung dan situasinya membaik.",
            "when": now - timedelta(days=22),
            "valence": 0.30,
            "significance": 0.60,
            "session": s2,
            "triggers": ["group_conflict"],
            "topics": ["friendship", "self_growth"],
            "people": ["dimas", "maya"],
            "emotions": [
                ("frustrated",  0.62, -0.55, "Frustrasi karena harus mengerjakan bagian orang lain."),
                ("proud",       0.68,  0.65, "Bangga karena bisa ngomong langsung dan situasinya membaik."),
            ],
            "thoughts": ["unfair_blame", "can_handle_this"],
            "behaviors": ["direct_talk"],
        },
        {
            "key": "pre_exam_overwhelm",
            "desc": "Seminggu sebelum UTS, Sari kewalahan dengan materi yang menumpuk, tidur tidak teratur, dan rindu keluarga.",
            "when": now - timedelta(days=8),
            "valence": -0.35,
            "significance": 0.68,
            "session": s3,
            "triggers": ["uts_approaching", "homesick", "sleep_irregular"],
            "topics": ["academic", "family", "sleep"],
            "people": ["mama", "papa", "bu_ani"],
            "emotions": [
                ("overwhelmed", 0.58, -0.52, "Materi terasa terlalu banyak untuk dihabiskan dalam seminggu."),
                ("nostalgic",   0.50, -0.20, "Kangen masakan Mama dan suasana rumah."),
                ("tired",       0.60, -0.48, "Kurang tidur mulai terasa di badan."),
            ],
            "thoughts": ["enough_to_fail", "can_handle_this"],
            "behaviors": ["late_study", "video_call"],
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
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.62)
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=4,
        severity_label="minimal",
        item_responses={"q1": 1, "q2": 0, "q3": 1, "q4": 1, "q5": 0, "q6": 0, "q7": 1, "q8": 0, "q9": 0},
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=45, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=5,
        severity_label="minimal",
        item_responses={"q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 0, "q6": 0, "q7": 1, "q8": 0, "q9": 0},
        delta_from_previous=1,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=21, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=6,
        severity_label="mild",
        item_responses={"q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 1, "q6": 0, "q7": 1, "q8": 0, "q9": 0},
        delta_from_previous=1,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=7, hours=1, minutes=20)),
        namespace=cfg.namespace,
    )

    for tkey, conf in [("academic", 0.78), ("friendship", 0.72), ("family", 0.70), ("self_growth", 0.75)]:
        await link_user_recurring_theme(cfg.user_id, topic_ids[tkey], s3, confidence=conf)

    for sess_id, summary, imp in [
        (s1, "Sari beradaptasi di kelompok baru, sedikit cemas tapi optimistis. PHQ-9 = 4 (minimal).", 0.55),
        (s2, "Sari atasi konflik kelompok dengan komunikasi langsung, berhasil. PHQ-9 = 5 (minimal).", 0.62),
        (s3, "Sari kewalahan menjelang UTS dan kangen keluarga, tapi masih bisa cope. PHQ-9 = 6 (mild).", 0.70),
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

    print(f"Seed normal_user (Sari) complete. user_id={cfg.user_id}, namespace={cfg.namespace}")
