"""utility/kg_seeder_scenario/scenario_2/seed.py

Seed Scenario 2 — Fajar: thriving CS student with mild job-hunting stress.

Fajar is a 3rd-year Computer Science student with a strong GPA (3.7/4.0).
He is generally positive, socially active, and coping well — but experiences
a brief imposter-syndrome episode when campus recruitment season starts.
The session arc shows him move from mild self-doubt to reframed confidence
via a CBT supersession.

Improvements over scenario_1:
  • Uses shared _common.py (no duplicated infrastructure)
  • PHQ-9 Assessment nodes via _write_assessment_node() — honouring the
    Go-Python split: Python seeder replicates what Go's WriteAssessment
    would write.
  • Thought SUPERSEDES arc via _write_supersession() — CBT reframe visible
    as a graph edge with bi-temporal provenance.
  • Same Trigger / Person / Topic referenced across MULTIPLE experiences
    (dense cross-node wiring, not just User-anchored spokes).
  • Behavior linked from both Thought and Emotion in the same turn.
  • Emotion explicitly linked to Topic (not only Experience → Topic).
  • All 18 canonical relationship types exercised at least once.

Usage:
  python -m utility.kg_seeder_scenario.scenario_2.seed --run
  python -m utility.kg_seeder_scenario.scenario_2.seed --purge
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from utility.kg_seeder_scenario._common import (
    SeedConfig,
    _build_arg_parser,
    _is_uuid,
    _iso,
    _now,
    _purge_namespace,
    _session_ids_for_namespace,
    _tag_node,
    _upsert_pg_embedding,
    _upsert_pg_user_and_sessions,
    _write_assessment_node,
    _write_supersession,
)


_DEFAULT_USER_ID  = "f3a8b84d-3fd4-57ca-a258-e4406c87af15"
_DEFAULT_NS       = "seed-scenario-2"
_SCENARIO_NAME    = "scenario2_fajar"
_PASSWORD_HASH    = "$2a$12$UAGUvJTsQjpSsx7YqU1D9ua1RvJbVmgbVBHAvFEwPAU3CHZGQpIZG"



async def _seed_graph(cfg: SeedConfig) -> None:
    from agentic.memory.pg_vector import embed_text, is_available as pgvector_available
    from agentic.memory.knowledge_graph.kg_writer import (
        BehaviorInput,
        EmotionInput,
        ExperienceInput,
        MemoryInput,
        SubjectInput,
        ThoughtInput,
        TriggerInput,
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
        TopicInput,
    )
    from agentic.memory.neo4j_client import get_client

    pg_ok = await pgvector_available()
    print(f"pgvector available: {'YES' if pg_ok else 'NO'}")

    now = _now()

    # Session timeline
    # s1: ~6 weeks ago — orientation / general wellbeing check-in
    # s2: ~4 weeks ago — thesis progress, positive momentum
    # s3: ~2 weeks ago — recruitment stress spikes (PHQ-9 administered)
    # s4: ~5 days ago  — post-interview debrief, confidence restored
    sids = _session_ids_for_namespace(cfg.namespace, count=4)
    s1, s2, s3, s4 = sids["s1"], sids["s2"], sids["s3"], sids["s4"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=42, hours=2),
            "ended_at":   now - timedelta(days=42, hours=1),
            "summary": (
                "Fajar merasa bersemangat dengan semester baru. "
                "Bercerita tentang proyek kelompok yang berjalan lancar "
                "dan teman-teman yang suportif."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=28, hours=1),
            "ended_at":   now - timedelta(days=28),
            "summary": (
                "Thesis proposal disetujui. Fajar senang dan termotivasi. "
                "Membahas teknik manajemen waktu yang sudah dipraktikkan."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=14, hours=3),
            "ended_at":   now - timedelta(days=14, hours=2),
            "summary": (
                "Recruitment season dimulai — Fajar mulai meragukan kemampuannya "
                "dibanding kandidat lain. PHQ-9 dilakukan: skor 5 (minimal). "
                "Sempat muncul pikiran imposter, sudah dieksplor bersama."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=5, hours=1),
            "ended_at":   now - timedelta(days=5),
            "summary": (
                "Fajar selesai wawancara teknis dan merasa senang. "
                "Merefleksikan bahwa persiapannya sendiri yang membawanya sejauh ini. "
                "Pikiran imposter berhasil di-reframe."
            ),
        },
    ]

    # Write User + Sessions to Neo4j
    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name               = 'Fajar Nugraha',
            u.display_name       = $display_name,
            u.preferred_language = $lang,
            u.created_at         = datetime(),
            u.consent_research   = false,
            u.active             = true
        SET u.seed_namespace = $ns

        WITH u
        UNWIND $sessions AS s
        MERGE (sess:Session {id: s.id})
        ON CREATE SET
            sess.started_at    = datetime(s.started_at),
            sess.last_activity = datetime(s.ended_at),
            sess.ended_at      = datetime(s.ended_at),
            sess.summary       = s.summary,
            sess.active        = true
        SET sess.seed_namespace = $ns
        MERGE (u)-[:HAD_SESSION]->(sess)
        """,
        {
            "user_id":      cfg.user_id,
            "display_name": _SCENARIO_NAME,
            "lang":         cfg.preferred_language,
            "ns":           cfg.namespace,
            "sessions": [
                {
                    "id":         r["id"],
                    "started_at": _iso(r["started_at"]),
                    "ended_at":   _iso(r["ended_at"]),
                    "summary":    r["summary"],
                }
                for r in session_rows
            ],
        },
    )
    await _upsert_pg_user_and_sessions(cfg, _SCENARIO_NAME, session_rows)

    # Topics
    topic_defs = {
        "achievement":    ("academic-achievement",  "academic"),
        "career":         ("career-planning",        "career"),
        "social_support": ("social-support",         "social"),
        "self_growth":    ("self-growth",            "identity"),
        "imposter":       ("imposter-syndrome",      "identity"),
    }
    # Use write_topic() so MERGE is by name_key — same as production.
    # This prevents duplicate nodes when real sessions write the same topic.
    topic_ids: dict[str, str] = {}
    for key, (name, category) in topic_defs.items():
        tid = await write_topic(TopicInput(
            name=name, category=category, sentiment=0.0,
            user_id=cfg.user_id, session_id=sids["s1"],
        ))
        topic_ids[key] = tid
        await _tag_node(node_id=tid, namespace=cfg.namespace)

    # People
    people: dict[str, str] = {}
    person_specs = [
        ("andi",    "Andi",        "friend",    0.85,  "supportive"),
        ("laila",   "Laila",       "partner",   0.90,  "supportive"),
        ("dr_andi", "Dr. Andika",  "professor", 0.65,  "supportive"),
        ("senior",  "Kak Rizky",   "mentor",    0.70,  "supportive"),
    ]
    for key, name, role, sent, quality in person_specs:
        pid = await write_subject(
            SubjectInput(
                name=name,
                role=role,
                sentiment=sent,
                relationship_quality=quality,
                subject_type="person",
                user_id=cfg.user_id,
                session_id=s1,
            )
        )
        people[key] = pid
        await _tag_node(node_id=pid, namespace=cfg.namespace)

    # Triggers
    # Reused across multiple experiences — this is the key cross-node wiring.
    trigger_specs = {
        "interview_nerves": ("academic", "ketakutan gagal saat wawancara kerja"),
        "thesis_deadline":  ("academic", "deadline milestone thesis"),
        "comparison":       ("social",   "membandingkan diri dengan kandidat lain"),
    }
    triggers: dict[str, str] = {}
    for key, (cat, desc) in trigger_specs.items():
        embedding = await embed_text(desc)
        tid = await write_trigger(
            TriggerInput(
                category=cat,
                description=desc,
                user_id=cfg.user_id,
                session_id=s3,   # first-seen in the stress session
                embedding=embedding,
            )
        )
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

    # Behaviors
    behavior_specs = {
        "prep_interviews": ("help_seeking",       "mempersiapkan latihan wawancara dengan senior", True),
        "journaling":      ("help_seeking",       "menulis jurnal refleksi harian",               True),
        "exercise":        ("exercise",           "olahraga pagi sebagai rutinitas harian",        True),
        "overthinking":    ("rumination",         "mengulang skenario terburuk interview",         False),
        "avoidance":       ("avoidance",          "menghindari melihat job portal karena cemas",   False),
    }
    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive) in behavior_specs.items():
        bid = await write_behavior(
            BehaviorInput(
                description=desc,
                category=cat,
                adaptive=adaptive,
                user_id=cfg.user_id,
                session_id=s3,
            )
        )
        behaviors[key] = bid
        await _tag_node(node_id=bid, namespace=cfg.namespace)

    # Thoughts
    # Two thoughts will be linked via SUPERSEDES (the CBT reframe arc).
    thought_specs = {
        "imposter":   ("Mungkin aku hanya beruntung dapat IPK tinggi, bukan karena kemampuanku sendiri",
                       "automatic", "mind_reading",   0.72),
        "comparison": ("Semua kandidat lain pasti lebih berpengalaman dari aku",
                       "automatic", "fortune_telling", 0.65),
        "reframed":   ("Persiapan dan kemampuanku sendiri yang membawa aku sejauh ini",
                       "automatic", None,              0.80),   # the post-CBT reframe
        "growth":     ("Setiap langkah kecil yang kulakukan adalah bukti bahwa aku berkembang",
                       "intermediate", None,           0.85),
    }
    thoughts: dict[str, str] = {}
    for key, (content, ttype, dist, bel) in thought_specs.items():
        embedding = await embed_text(content)
        sess = s4 if key in ("reframed", "growth") else s3
        tid = await write_thought(
            ThoughtInput(
                content=content,
                thought_type=ttype,
                distortion=dist,
                believability=bel,
                user_id=cfg.user_id,
                session_id=sess,
                embedding=embedding,
            )
        )
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

    # SUPERSEDES arc
    # (reframed:Thought)-[:SUPERSEDES]->(imposter:Thought)
    # Models the CBT reframe that happened in session 4.
    await _write_supersession(
        old_thought_id=thoughts["imposter"],
        new_thought_id=thoughts["reframed"],
        reason="CBT reframe: user traced evidence of consistent preparation and skill",
        session_id=s4,
        at=_iso(now - timedelta(days=5, hours=1, minutes=20)),
    )

    # Emotion helper
    async def mk_emotion(
        label: str, intensity: float, valence: float,
        source_text: str, sess: str,
    ) -> str:
        eid = await write_emotion(
            EmotionInput(
                label=label,
                intensity=intensity,
                valence=valence,
                source_text=source_text,
                user_id=cfg.user_id,
                session_id=sess,
            )
        )
        await _tag_node(node_id=eid, namespace=cfg.namespace)
        return eid

    # Experiences
    # Key design: each experience connects to Trigger, Person, Topic, Emotion, Thought,
    # and Behavior across multiple sessions — producing a dense, non-spoke graph.
    experience_rows: list[dict[str, Any]] = [
        # Session 1 experiences
        {
            "key":          "group_project_win",
            "desc":         "Proyek kelompok selesai lebih awal dan mendapat pujian dosen.",
            "when":         now - timedelta(days=45),
            "valence":      0.85,
            "significance": 0.75,
            "session":      s1,
            "triggers":     [],
            "topics":       ["achievement", "social_support"],
            "people":       ["andi"],
            "emotions":     [
                ("proud",     0.80, 0.75, "Aku bangga dengan hasilnya."),
                ("grateful",  0.70, 0.70, "Senang punya tim yang solid."),
            ],
            "thoughts":  ["growth"],
            "behaviors": ["journaling"],
        },
        {
            "key":          "morning_routine",
            "desc":         "Mulai rutinitas olahraga pagi dan merasakan peningkatan energi.",
            "when":         now - timedelta(days=40),
            "valence":      0.75,
            "significance": 0.60,
            "session":      s1,
            "triggers":     [],
            "topics":       ["self_growth"],
            "people":       [],
            "emotions":     [
                ("hopeful",   0.70, 0.65, "Aku merasa lebih energik dan termotivasi."),
            ],
            "thoughts":  ["growth"],
            "behaviors": ["exercise"],
        },
        # Session 2 experiences
        {
            "key":          "thesis_approval",
            "desc":         "Proposal thesis disetujui Dr. Andika dengan komentar positif.",
            "when":         now - timedelta(days=30),
            "valence":      0.90,
            "significance": 0.90,
            "session":      s2,
            "triggers":     ["thesis_deadline"],   # deadline exists, but positive framing
            "topics":       ["achievement", "career"],
            "people":       ["dr_andi"],
            "emotions":     [
                ("excited",   0.85, 0.80, "Aku sangat senang proposalku diterima!"),
                ("motivated", 0.80, 0.75, "Aku ingin segera mulai penelitiannya."),
            ],
            "thoughts":  ["growth"],
            "behaviors": ["journaling"],
        },
        {
            "key":          "mentor_coffee",
            "desc":         "Kopi bareng Kak Rizky yang berbagi pengalaman magang di perusahaan tech.",
            "when":         now - timedelta(days=26),
            "valence":      0.70,
            "significance": 0.65,
            "session":      s2,
            "triggers":     ["interview_nerves"],  # career topic triggers mild anticipation
            "topics":       ["career", "social_support"],
            "people":       ["senior"],
            "emotions":     [
                ("hopeful",   0.65, 0.60, "Cerita Kak Rizky bikin aku semangat."),
                ("anxious",   0.30, -0.20, "Ada sedikit was-was soal proses seleksi."),
            ],
            "thoughts":  ["imposter"],
            "behaviors": ["journaling"],
        },
        # Session 3 experiences (stress peak)
        {
            "key":          "job_fair_overwhelm",
            "desc":         "Melihat profil kandidat lain di job fair dan merasa tidak sebanding.",
            "when":         now - timedelta(days=16),
            "valence":      -0.55,
            "significance": 0.80,
            "session":      s3,
            "triggers":     ["comparison", "interview_nerves"],  # two triggers for one experience
            "topics":       ["imposter", "career"],
            "people":       ["andi"],
            "emotions":     [
                ("anxious",      0.70, -0.60, "Aku panik melihat CV orang-orang lain."),
                ("insecure",     0.65, -0.65, "Aku merasa tidak cukup baik."),
            ],
            "thoughts":  ["imposter", "comparison"],
            "behaviors": ["overthinking", "avoidance"],
        },
        {
            "key":          "laila_support",
            "desc":         "Laila mendengarkan ceritaku soal rasa tidak percaya diri dan meyakinkanku.",
            "when":         now - timedelta(days=15),
            "valence":      0.50,
            "significance": 0.70,
            "session":      s3,
            "triggers":     [],
            "topics":       ["social_support", "self_growth"],
            "people":       ["laila"],
            "emotions":     [
                ("grateful", 0.75, 0.65, "Laila selalu tahu cara menenangkanku."),
                ("hopeful",  0.55, 0.45, "Mungkin aku sudah terlalu keras pada diri sendiri."),
            ],
            "thoughts":  ["growth"],
            "behaviors": ["journaling"],
        },
        # Session 4 experiences (resolution)
        {
            "key":          "mock_interview",
            "desc":         "Latihan wawancara dengan Kak Rizky — performa jauh lebih baik dari ekspektasi.",
            "when":         now - timedelta(days=9),
            "valence":      0.75,
            "significance": 0.85,
            "session":      s4,
            "triggers":     ["interview_nerves"],  # same trigger, different emotional outcome
            "topics":       ["career", "self_growth"],
            "people":       ["senior"],
            "emotions":     [
                ("confident",  0.75, 0.70, "Ternyata aku bisa menjawab dengan baik."),
                ("surprised",  0.60, 0.55, "Tidak menyangka bisa melewatinya dengan lancar."),
            ],
            "thoughts":  ["reframed", "growth"],
            "behaviors": ["prep_interviews"],
        },
        {
            "key":          "actual_interview",
            "desc":         "Wawancara teknis selesai. Interviewer tersenyum dan bilang 'good job'.",
            "when":         now - timedelta(days=5, hours=4),
            "valence":      0.90,
            "significance": 0.95,
            "session":      s4,
            "triggers":     ["interview_nerves"],  # trigger present, but response is coping
            "topics":       ["career", "achievement", "imposter"],
            "people":       ["laila", "dr_andi"],
            "emotions":     [
                ("proud",     0.85, 0.80, "Aku berhasil!"),
                ("relieved",  0.80, 0.70, "Perasaan lega yang luar biasa."),
                ("grateful",  0.75, 0.70, "Terima kasih atas semua dukungan yang kudapat."),
            ],
            "thoughts":  ["reframed"],
            "behaviors": ["prep_interviews", "exercise"],
        },
    ]

    exp_ids: dict[str, str] = {}

    for row in experience_rows:
        embedding = await embed_text(row["desc"])
        exp_id = await write_experience(
            ExperienceInput(
                description=row["desc"],
                occurred_at=_iso(row["when"]),
                extracted_at=_iso(now),
                valence=row["valence"],
                significance=row["significance"],
                user_id=cfg.user_id,
                session_id=row["session"],
                embedding=embedding,
            )
        )
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

        # Triggers → Experience (relationship 1)
        for tkey in row["triggers"]:
            await link_experience_to_trigger(exp_id, triggers[tkey], row["session"])

        # Experience → Topic (relationship 17)
        for tkey in row["topics"]:
            await link_to_topic(exp_id, "Experience", topic_ids[tkey], row["session"])

        # Experience → Person (relationship 16)
        for pkey in row["people"]:
            await link_experience_to_person(exp_id, people[pkey], row["session"])

        # Emotions → Experience + downstream CBT chain
        emotion_ids: list[str] = []
        for (lab, inten, val, txt) in row["emotions"]:
            eid = await mk_emotion(lab, float(inten), float(val), txt, row["session"])
            emotion_ids.append(eid)

            # (Experience)-[:TRIGGERED_EMOTION]->(Emotion) — relationship 2
            await link_experience_to_emotion(exp_id, eid, row["session"])

            # (Emotion)-[:RELATED_TO_TOPIC]->(Topic) — relationship 17 (Emotion variant)
            for tkey in row["topics"][:1]:   # link first topic to each emotion
                await link_to_topic(eid, "Emotion", topic_ids[tkey], row["session"])

        # Thoughts: bi-directional cross-links with all emotions in this experience
        for tkey in row["thoughts"]:
            for eid in emotion_ids:
                # (Emotion)-[:ACTIVATED_THOUGHT]->(Thought) — relationship 3
                await link_emotion_to_thought(eid, thoughts[tkey], row["session"])
                # (Thought)<-[:ASSOCIATED_WITH]->(Emotion) bidirectional — relationship 4
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.80)

        # Behaviors: linked from BOTH emotion and thought — rich cross-node wiring
        for bkey in row["behaviors"]:
            if emotion_ids:
                # (Emotion)-[:LED_TO_BEHAVIOR]->(Behavior) — relationship 5
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                # (Thought)-[:LED_TO_BEHAVIOR]->(Behavior) — relationship 5
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    # PHQ-9 Assessment nodes
    # Mirrors what Go's WriteAssessment would produce for two administrations.
    # s1 administration: score 3 (minimal)
    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=3,
        severity_label="minimal",
        item_responses={
            "q1": 0, "q2": 0, "q3": 0, "q4": 1,
            "q5": 0, "q6": 0, "q7": 1, "q8": 0, "q9": 1,
        },
        delta_from_previous=None,
        q9_score=1,
        administered_at=_iso(now - timedelta(days=42, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    # s3 administration: score 5 (minimal, but slightly elevated due to stress)
    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=5,
        severity_label="minimal",
        item_responses={
            "q1": 1, "q2": 1, "q3": 0, "q4": 1,
            "q5": 0, "q6": 0, "q7": 1, "q8": 1, "q9": 0,
        },
        delta_from_previous=2,   # +2 from last session (still minimal)
        q9_score=0,
        administered_at=_iso(now - timedelta(days=14, hours=2, minutes=40)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id: {phq9_s3}")

    # User recurring themes (relationship 9)
    for tkey in ("achievement", "career", "self_growth", "social_support"):
        await link_user_recurring_theme(
            cfg.user_id, topic_ids[tkey], s4, confidence=0.85,
        )

    # Session memories (relationship 15: Session-[:CONTAINS_MEMORY]->Memory)
    memory_rows = [
        (s1, "Fajar bersemangat di awal semester, proyek kelompok berhasil dan rutinitas olahraga terbentuk.", 0.60),
        (s2, "Proposal thesis disetujui; Fajar mulai mendapat gambaran tentang dunia kerja dari seniornya.", 0.70),
        (s3, "Recruitment stress memunculkan imposter syndrome ringan; PHQ-9 skor 5, masih minimal. CBT dimulai.", 0.80),
        (s4, "Setelah latihan dan wawancara nyata, Fajar berhasil me-reframe imposter syndrome menjadi keyakinan diri.", 0.85),
    ]
    for sess_id, summary, imp in memory_rows:
        embedding = await embed_text(summary)
        mem_id = await write_memory(
            MemoryInput(
                summary=summary,
                importance=float(imp),
                user_id=cfg.user_id,
                session_id=sess_id,
                embedding=embedding,
            )
        )
        await _tag_node(node_id=mem_id, namespace=cfg.namespace)
        await _upsert_pg_embedding(
            table="memory_embeddings",
            user_id=cfg.user_id,
            neo4j_node_id=mem_id,
            content=summary,
            embedding=embedding,
            importance=float(imp),
        )
        # Explicit Session → Memory link (relationship 15)
        await link_session_to_memory(sess_id, mem_id, sess_id)

    print("Seed scenario 2 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (1 SUPERSEDES arc)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print(f"  assessments: 2 (PHQ-9)")


# CLI entry-point

async def _main_async(args) -> int:
    from agentic.memory.neo4j_client import init_client

    if not _is_uuid(args.user_id) and not args.allow_non_uuid_user_id:
        raise SystemExit(
            "--user-id must be a UUID. Pass --allow-non-uuid-user-id for Neo4j-only seeding."
        )

    cfg = SeedConfig(
        user_id=args.user_id,
        namespace=args.namespace,
        password_hash=_PASSWORD_HASH,
        preferred_language=args.lang,
    )
    await init_client()

    if args.purge:
        session_ids = list(_session_ids_for_namespace(cfg.namespace, count=4).values())
        await _purge_namespace(cfg.namespace, session_ids, user_id=cfg.user_id)
        return 0

    if not args.run:
        print("Nothing to do. Pass --run to seed, or --purge to delete.")
        return 2

    await _seed_graph(cfg)
    return 0


def main() -> int:
    ap = _build_arg_parser(
        description="Seed KG Scenario 2 — Fajar (thriving student)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
