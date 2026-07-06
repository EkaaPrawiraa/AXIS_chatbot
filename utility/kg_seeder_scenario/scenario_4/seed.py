"""utility/kg_seeder_scenario/scenario_4/seed.py

Seed Scenario 4 — Budi: young professional with startup burnout.

Budi is a 26-year-old software developer at an early-stage startup.
Over 10 weeks he progresses from moderate depression (PHQ-9 = 11)
to moderately-severe (PHQ-9 = 17, near the crisis threshold of 20).
His arc shows:
  - Rapid PHQ-9 deterioration across 4 sessions (+6 delta = a clinically
    significant worsening in a short window)
  - Burnout-specific behavior pattern: overworking → physical symptoms →
    social isolation → nihilism
  - Two SUPERSEDES thought arcs: "grinding is the only path" → "rest is
    productive", and "no one can do this but me" → "delegation is strength"
  - A Person node (Pak Hendra, CEO) appearing in multiple experiences
    with consistently negative sentiment, illustrating how the graph
    tracks interpersonal patterns over time
  - q9_score > 0 in the final session, which in production would trigger
    the Go crisis pathway review

Usage:
  python -m utility.kg_seeder_scenario.scenario_4.seed --run
  python -m utility.kg_seeder_scenario.scenario_4.seed --purge
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

_DEFAULT_USER_ID = "9807189d-3889-5254-b25e-d9f6d0c865da"
_DEFAULT_NS      = "seed-scenario-4"
_SCENARIO_NAME   = "scenario4_budi"
_PASSWORD_HASH   = "$2a$12$u0rRb7fUzUaracmGg3m/GORRG/EeMD9hkqoefc2AVrmSVbamycgWa"


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
    # s1: ~10 weeks ago — first session, moderate depression, work complaints
    # s2: ~7 weeks ago  — sleep deteriorating, relationship strain
    # s3: ~4 weeks ago  — crisis signs emerging, PHQ-9 = 15 (moderately severe)
    # s4: ~1 week ago   — near-crisis, PHQ-9 = 17, q9_score = 1
    sids = _session_ids_for_namespace(cfg.namespace, count=4)
    s1, s2, s3, s4 = sids["s1"], sids["s2"], sids["s3"], sids["s4"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=70, hours=2),
            "ended_at":   now - timedelta(days=70, hours=1),
            "summary": (
                "Budi bercerita tentang tekanan kerja yang intens di startup. "
                "Lembur 70+ jam per minggu terasa normal tapi melelahkan. "
                "PHQ-9 dilakukan: skor 11 (moderate)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=49, hours=2),
            "ended_at":   now - timedelta(days=49, hours=1),
            "summary": (
                "Tidur semakin buruk — 4 jam per malam, bangun dengan anxiety. "
                "Budi dan Sari semakin jarang berbicara karena Budi selalu terlambat pulang. "
                "PHQ-9 naik ke 13 (moderate, delta +2)."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=28, hours=2),
            "ended_at":   now - timedelta(days=28, hours=1),
            "summary": (
                "Tanda burnout klinis muncul: sinisme, detachment emosional, rasa tidak berguna. "
                "Budi berkata 'aku sudah tidak peduli lagi apakah startup ini berhasil'. "
                "PHQ-9 = 15 (moderately severe, delta +2)."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=7, hours=2),
            "ended_at":   now - timedelta(days=7, hours=1),
            "summary": (
                "Budi menyebut 'kadang aku pikir semuanya lebih mudah kalau aku tidak ada'. "
                "PHQ-9 = 17 (moderately severe, delta +2). q9 = 1 — safety protokol diaktifkan. "
                "Budi menyangkal rencana konkret tapi mengakui kelelahan ekstrem."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name               = 'Budi Santoso',
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
        "burnout":        ("work-burnout",           "career"),
        "overwork":       ("chronic-overwork",       "career"),
        "isolation":      ("social-isolation",       "social"),
        "sleep":          ("sleep-deprivation",      "health"),
        "identity":       ("identity-work-fusion",   "identity"),
        "nihilism":       ("nihilistic-thinking",    "mental_health"),
        "relationship":   ("partner-neglect",        "social"),
    }
    # Use write_topic() so MERGE is by name_key — same as production.
    topic_ids: dict[str, str] = {}
    for key, (name, category) in topic_defs.items():
        tid = await write_topic(TopicInput(
            name=name, category=category, sentiment=0.0,
            user_id=cfg.user_id, session_id=s1,
        ))
        topic_ids[key] = tid
        await _tag_node(node_id=tid, namespace=cfg.namespace)

    # People
    # Pak Hendra (CEO) appears in multiple negative experiences — tracking
    # relationship deterioration over time via the same Person node.
    people: dict[str, str] = {}
    person_specs = [
        ("hendra", "Pak Hendra",  "manager",  -0.75, "negative"),
        ("sari",   "Sari",        "partner",   0.60,  "complicated"),
        ("dimas",  "Dimas",       "colleague", 0.30,  "neutral"),
        ("ibu",    "Ibu",         "parent",    0.65,  "supportive"),
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
    trigger_specs = {
        "ceo_pressure":   ("work",      "tekanan langsung dari CEO untuk deliver lebih cepat"),
        "sleep_debt":     ("health",    "kurang tidur kronis yang memperburuk mood dan kognitif"),
        "financial_fear": ("financial", "ketakutan startup tutup dan kehilangan pekerjaan"),
        "isolation":      ("social",    "tidak punya waktu untuk bertemu teman atau keluarga"),
        "product_fail":   ("work",      "fitur yang dikerjakan berminggu-minggu di-rollback"),
    }
    triggers: dict[str, str] = {}
    for key, (cat, desc) in trigger_specs.items():
        embedding = await embed_text(desc)
        tid = await write_trigger(
            TriggerInput(
                category=cat,
                description=desc,
                user_id=cfg.user_id,
                session_id=s1,
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
            importance=0.70,
        )

    # Behaviors
    behavior_specs = {
        "overwork":       ("avoidance",        "kerja melebihi jam kerja untuk menghindari pikiran gelap",   False),
        "skip_meals":     ("avoidance",        "lupa makan siang karena terus coding",                       False),
        "social_cancel":  ("social_withdrawal","membatalkan rencana sosial di menit-menit terakhir",         False),
        "doomscroll":     ("rumination",       "doomscrolling berita startup failures larut malam",          False),
        "substance":      ("substance_use",    "minum kopi 6 cup sehari untuk tetap berfungsi",             False),
        "call_ibu":       ("help_seeking",     "menelepon Ibu ketika merasa overwhelmed",                    True),
        "short_walk":     ("exercise",         "jalan kaki 10 menit saat istirahat meski jarang",            True),
        "talk_dimas":     ("help_seeking",     "berbagi kekhawatiran dengan Dimas di kantor",                True),
    }
    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive) in behavior_specs.items():
        bid = await write_behavior(
            BehaviorInput(
                description=desc,
                category=cat,
                adaptive=adaptive,
                user_id=cfg.user_id,
                session_id=s1,
            )
        )
        behaviors[key] = bid
        await _tag_node(node_id=bid, namespace=cfg.namespace)

    # Thoughts
    # Two SUPERSEDES arcs planted in s4 (early intervention attempt):
    #   Arc A: "grinding is the only path" → "rest is productive"
    #   Arc B: "no one can do this but me" → "delegation is strength"
    # Note: both reframes are fragile in this scenario — Budi only partially
    # accepts them (believability 0.45–0.50 on the reframed thoughts).
    thought_specs = {
        # Arc A
        "must_grind":       ("Kalau aku berhenti sebentar saja, semuanya akan hancur",
                              "intermediate", "catastrophizing",  0.88),
        "rest_productive":  ("Istirahat adalah bagian dari produktivitas, bukan kelemahan",
                              "intermediate",  None,              0.45),   # fragile reframe
        # Arc B
        "only_me":          ("Tidak ada yang bisa menyelesaikan ini selain aku sendiri",
                              "intermediate", "mind_reading",     0.82),
        "delegation_ok":    ("Mendelegasikan tugas adalah tanda kepercayaan diri, bukan kelemahan",
                              "intermediate",  None,              0.50),   # fragile reframe
        # Dark spiral thoughts (not reframed yet)
        "no_value":         ("Aku tidak memberikan nilai apapun meski sudah kerja sekeras ini",
                              "core_belief",  "labeling",         0.80),
        "escape_thoughts":  ("Kadang aku pikir semuanya lebih mudah kalau aku tidak ada",
                              "automatic",    "emotional_reasoning", 0.55),  # q9-level thought
        "sunk_cost":        ("Aku sudah terlalu dalam untuk menyerah, meski aku tahu ini menyakitiku",
                              "automatic",    "emotional_reasoning", 0.75),
        "worthless_effort": ("Tidak peduli seberapa keras aku kerja, tidak ada yang berubah",
                              "automatic",    "overgeneralization",  0.78),
    }
    thoughts: dict[str, str] = {}
    for key, (content, ttype, dist, bel) in thought_specs.items():
        if key in ("rest_productive", "delegation_ok"):
            sess = s4
        elif key in ("escape_thoughts",):
            sess = s4
        elif key in ("no_value", "worthless_effort"):
            sess = s3
        else:
            sess = s2
        embedding = await embed_text(content)
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

    # SUPERSEDES arcs
    # Both reframes attempted in s4 but with low believability — shows
    # partial CBT progress that still needs follow-up.
    await _write_supersession(
        old_thought_id=thoughts["must_grind"],
        new_thought_id=thoughts["rest_productive"],
        reason="Therapist prompted Budi to list one time rest actually helped him perform better — he recalled a camping trip",
        session_id=s4,
        at=_iso(now - timedelta(days=7, hours=1, minutes=30)),
    )
    await _write_supersession(
        old_thought_id=thoughts["only_me"],
        new_thought_id=thoughts["delegation_ok"],
        reason="Budi acknowledged Dimas had successfully handled the last deployment; partial acceptance",
        session_id=s4,
        at=_iso(now - timedelta(days=7, hours=1, minutes=10)),
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
    experience_rows: list[dict[str, Any]] = [
        # s1: Moderate overwork
        {
            "key":          "sprint_crunch",
            "desc":         "Dua minggu sprint tanpa hari off, deadline dimajukan Pak Hendra tanpa pemberitahuan.",
            "when":         now - timedelta(days=75),
            "valence":      -0.65,
            "significance": 0.80,
            "session":      s1,
            "triggers":     ["ceo_pressure", "sleep_debt"],
            "topics":       ["burnout", "overwork"],
            "people":       ["hendra"],
            "emotions":     [
                ("frustrated",   0.80, -0.70, "Pak Hendra memajukan deadline lagi tanpa diskusi."),
                ("exhausted",    0.85, -0.80, "Aku tidak ingat kapan terakhir tidur 7 jam."),
            ],
            "thoughts":  ["must_grind", "only_me"],
            "behaviors": ["overwork", "skip_meals"],
        },
        {
            "key":          "sari_dinner_cancel",
            "desc":         "Membatalkan makan malam ulang tahun Sari karena ada bug production di menit-menit terakhir.",
            "when":         now - timedelta(days=72),
            "valence":      -0.75,
            "significance": 0.85,
            "session":      s1,
            "triggers":     ["ceo_pressure", "isolation"],
            "topics":       ["relationship", "burnout"],
            "people":       ["sari"],
            "emotions":     [
                ("guilty",     0.80, -0.75, "Sari menangis. Aku tahu aku salah tapi tidak bisa berbuat apa-apa."),
                ("trapped",    0.75, -0.80, "Rasanya seperti terjebak antara pekerjaan dan orang yang kucintai."),
            ],
            "thoughts":  ["must_grind", "sunk_cost"],
            "behaviors": ["social_cancel", "overwork"],
        },
        # s2: Sleep and relationship deteriorate
        {
            "key":          "4am_coding",
            "desc":         "Bangun jam 4 pagi karena tidak bisa tidur, langsung buka laptop dan coding sampai subuh.",
            "when":         now - timedelta(days=52),
            "valence":      -0.80,
            "significance": 0.80,
            "session":      s2,
            "triggers":     ["sleep_debt", "financial_fear"],
            "topics":       ["sleep", "burnout", "nihilism"],
            "people":       [],
            "emotions":     [
                ("numb",         0.70, -0.70, "Aku sudah tidak merasakan apa-apa, hanya melakukan apa yang harus dilakukan."),
                ("hopeless",     0.65, -0.75, "Bahkan setelah semua ini, tidak ada yang berubah."),
            ],
            "thoughts":  ["worthless_effort", "must_grind"],
            "behaviors": ["overwork", "substance"],
        },
        {
            "key":          "dimas_talk",
            "desc":         "Dimas melihat Budi tampak lelah dan mengajak bicara; Budi berbagi sedikit tentang tekanan kerja.",
            "when":         now - timedelta(days=50),
            "valence":      0.20,
            "significance": 0.55,
            "session":      s2,
            "triggers":     ["isolation"],
            "topics":       ["isolation", "burnout"],
            "people":       ["dimas"],
            "emotions":     [
                ("relieved",   0.45, 0.35, "Lega ada yang bertanya kabarku."),
                ("vulnerable", 0.50, -0.20, "Tidak biasa bercerita soal ini ke orang kerja."),
            ],
            "thoughts":  ["only_me"],
            "behaviors": ["talk_dimas"],
        },
        # s3: Burnout clinical signs
        {
            "key":          "feature_rollback",
            "desc":         "Fitur yang Budi kerjakan selama 3 minggu di-rollback karena perubahan arah produk.",
            "when":         now - timedelta(days=31),
            "valence":      -0.85,
            "significance": 0.90,
            "session":      s3,
            "triggers":     ["product_fail", "ceo_pressure"],
            "topics":       ["burnout", "nihilism", "identity"],
            "people":       ["hendra"],
            "emotions":     [
                ("devastated",  0.85, -0.85, "Tiga minggu kerja tidak berguna sama sekali."),
                ("cynical",     0.80, -0.80, "Aku sudah tidak peduli apakah startup ini berhasil."),
                ("angry",       0.70, -0.65, "Pak Hendra tidak pernah minta pendapat tim."),
            ],
            "thoughts":  ["no_value", "worthless_effort", "must_grind"],
            "behaviors": ["doomscroll", "social_cancel"],
        },
        {
            "key":          "ibu_call_s3",
            "desc":         "Menelepon Ibu; Ibu khawatir melihat perubahan suara Budi yang terdengar lesu dan kosong.",
            "when":         now - timedelta(days=29),
            "valence":      -0.30,
            "significance": 0.65,
            "session":      s3,
            "triggers":     ["isolation"],
            "topics":       ["isolation", "relationship"],
            "people":       ["ibu"],
            "emotions":     [
                ("sad",       0.70, -0.65, "Aku hampir menangis waktu Ibu bilang kangen."),
                ("grateful",  0.45, 0.35, "Setidaknya ada yang masih peduli."),
            ],
            "thoughts":  ["no_value"],
            "behaviors": ["call_ibu"],
        },
        # s4: Near-crisis
        {
            "key":          "hendra_yell",
            "desc":         "Pak Hendra membentak Budi di depan tim dalam rapat karena bug di production.",
            "when":         now - timedelta(days=9),
            "valence":      -0.95,
            "significance": 0.95,
            "session":      s4,
            "triggers":     ["ceo_pressure", "product_fail"],
            "topics":       ["burnout", "identity", "nihilism"],
            "people":       ["hendra"],
            "emotions":     [
                ("humiliated", 0.90, -0.90, "Dibentak di depan semua orang, aku tidak tahu bagaimana harus bereaksi."),
                ("numb",       0.85, -0.85, "Setelah itu aku hanya duduk diam. Tidak ada energi untuk marah."),
                ("hopeless",   0.85, -0.90, "Mungkin aku memang tidak layak ada di sini."),
            ],
            "thoughts":  ["escape_thoughts", "no_value", "worthless_effort"],
            "behaviors": ["overwork", "doomscroll"],
        },
        {
            "key":          "walk_alone_s4",
            "desc":         "Keluar kantor sendirian saat break, duduk di taman, berusaha bernapas pelan-pelan.",
            "when":         now - timedelta(days=8),
            "valence":      -0.20,
            "significance": 0.60,
            "session":      s4,
            "triggers":     ["sleep_debt"],
            "topics":       ["burnout", "isolation"],
            "people":       [],
            "emotions":     [
                ("exhausted", 0.80, -0.75, "Lelah yang tidak bisa dijelaskan dengan kata-kata."),
                ("yearning",  0.55, -0.30, "Aku rindu versi diriku yang dulu — yang bisa menikmati kerja."),
            ],
            "thoughts":  ["rest_productive", "delegation_ok"],
            "behaviors": ["short_walk"],
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

        for tkey in row["triggers"]:
            await link_experience_to_trigger(exp_id, triggers[tkey], row["session"])

        for tkey in row["topics"]:
            await link_to_topic(exp_id, "Experience", topic_ids[tkey], row["session"])

        for pkey in row["people"]:
            await link_experience_to_person(exp_id, people[pkey], row["session"])

        emotion_ids: list[str] = []
        for (lab, inten, val, txt) in row["emotions"]:
            eid = await mk_emotion(lab, float(inten), float(val), txt, row["session"])
            emotion_ids.append(eid)
            await link_experience_to_emotion(exp_id, eid, row["session"])
            for tkey in row["topics"][:2]:
                await link_to_topic(eid, "Emotion", topic_ids[tkey], row["session"])

        for tkey in row["thoughts"]:
            for eid in emotion_ids:
                await link_emotion_to_thought(eid, thoughts[tkey], row["session"])
                await link_thought_emotion_association(
                    thoughts[tkey], eid, row["session"], strength=0.90,
                )

        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    # PHQ-9 Assessment nodes
    # s1: score=11, moderate
    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=11,
        severity_label="moderate",
        item_responses={
            "q1": 2, "q2": 2, "q3": 1, "q4": 2,
            "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 0,
        },
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=70, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    # s2: score=13, moderate (delta=+2)
    phq9_s2 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=13,
        severity_label="moderate",
        item_responses={
            "q1": 2, "q2": 2, "q3": 2, "q4": 2,
            "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 1,
        },
        delta_from_previous=2,
        q9_score=1,    # q9=1: passive ideation first appears — safety check
        administered_at=_iso(now - timedelta(days=49, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s2 id: {phq9_s2}")

    # s3: score=15, moderately_severe (delta=+2)
    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=15,
        severity_label="moderately_severe",
        item_responses={
            "q1": 2, "q2": 3, "q3": 2, "q4": 2,
            "q5": 1, "q6": 1, "q7": 1, "q8": 2, "q9": 1,
        },
        delta_from_previous=2,
        q9_score=1,
        administered_at=_iso(now - timedelta(days=28, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id (mod-severe): {phq9_s3}")

    # s4: score=17, moderately_severe (delta=+2, total +6 over 10 weeks)
    # q9_score=1: triggers safety protocol review in production
    phq9_s4 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s4,
        instrument="PHQ-9",
        score=17,
        severity_label="moderately_severe",
        item_responses={
            "q1": 2, "q2": 3, "q3": 2, "q4": 2,
            "q5": 2, "q6": 2, "q7": 1, "q8": 2, "q9": 1,
        },
        delta_from_previous=2,
        q9_score=1,    # sustained q9 — safety escalation expected in production
        administered_at=_iso(now - timedelta(days=7, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s4 id (near-crisis): {phq9_s4}")

    # User recurring themes
    for tkey, conf in [
        ("burnout",    0.95),
        ("overwork",   0.90),
        ("nihilism",   0.85),
        ("isolation",  0.80),
        ("identity",   0.80),
    ]:
        await link_user_recurring_theme(
            cfg.user_id, topic_ids[tkey], s4, confidence=conf,
        )

    # Session memories
    memory_rows = [
        (s1, "Budi overworked dan kelelahan. PHQ-9 = 11 (moderate). Sari mulai diabaikan.", 0.75),
        (s2, "Tidur 4 jam/malam, hubungan dengan Sari memburuk. PHQ-9 = 13 (+2). q9=1 pertama kali.", 0.80),
        (s3, "Feature di-rollback, sinisme memuncak. PHQ-9 = 15 (mod-severe, +2). Tanda burnout klinis.", 0.88),
        (s4, "Dibentak Pak Hendra di depan tim. PHQ-9 = 17 (+2). q9=1 — safety protokol diaktifkan. CBT reframe parsial.", 0.95),
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
        await link_session_to_memory(sess_id, mem_id, sess_id)

    print("Seed scenario 4 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (2 partial SUPERSEDES arcs)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print(f"  assessments: 4 (PHQ-9 arc 11→13→15→17, q9>0 in s2–s4)")


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
        description="Seed KG Scenario 4 — Budi (burnout, near-crisis arc)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
