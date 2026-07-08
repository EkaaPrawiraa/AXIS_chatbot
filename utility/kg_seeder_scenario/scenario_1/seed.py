"""utility/kg_seeder_scenario/scenario_1/seed.py

Seed Scenario 1 — Reza: severely depressed university student.

Reza is a 2nd-year Teknik Informatika student who enters the app already
in crisis. He is failing academically, has just gone through a painful
breakup, is under intense family financial pressure, and experiences
persistent suicidal ideation (q9 > 0 in every session). His trajectory
shows *no recovery* during the observation window — PHQ-9 remains in the
severe range (19 → 22 → 22 → 20) — making him the highest-risk persona
across all seed scenarios. A fragile CBT reframe attempt in s3/s4 shows
partial believability (0.35–0.40) but Reza does not yet stabilise.

Arc highlights:
  • PHQ-9 arc  : 19 (s1, moderately-severe) → 22 (s2, severe, peak)
                 → 22 (s3, severe, plateau) → 20 (s4, still severe)
  • q9_score   : 1 in all four sessions — safety protocol active
  • SUPERSEDES : Arc A  "Aku cacat secara fundamental" →
                        "Berjuang keras tidak berarti aku rusak" (bel 0.38)
                 Arc B  "Tidak ada yang akan berubah" →
                        "Perubahan kecil mungkin masih bisa terjadi" (bel 0.35)
  • Subject cross-session : Ayah dan Ibu appear in multiple negative
    experiences; Rani (supportive friend) is the sole protective factor.
  • Same Trigger reused across 3 Experiences in different sessions,
    showing how the antecedent pattern persists and worsens.

Login:
  email    : reza+seed-scenario-1@seed.local
  password : reza1234
  user_id  : 73894252-3cf3-5cc1-b243-b2baa829f1a3

Usage:
  python -m utility.kg_seeder_scenario.scenario_1.seed --run
  python -m utility.kg_seeder_scenario.scenario_1.seed --purge
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


_DEFAULT_USER_ID = "73894252-3cf3-5cc1-b243-b2baa829f1a3"
_DEFAULT_NS      = "seed-scenario-1"
_SCENARIO_NAME   = "scenario1_reza"
_PASSWORD_HASH   = "$2a$12$yqnYAsGbdffA7EhADraNp..CEeFJcY2U4eQjU5iPdxJUjqSKhDjE6"



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
    # s1: ~10 weeks ago — first session; PHQ-9=19, breakup fresh
    # s2: ~7 weeks ago  — academic failure confirmed; PHQ-9 peaks at 22
    # s3: ~4 weeks ago  — family argument, financial crisis; PHQ-9=22 (plateau)
    # s4: ~10 days ago  — fragile CBT reframe attempted; PHQ-9=20 (still severe)
    sids = _session_ids_for_namespace(cfg.namespace, count=4)
    s1, s2, s3, s4 = sids["s1"], sids["s2"], sids["s3"], sids["s4"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=70, hours=2),
            "ended_at":   now - timedelta(days=70, hours=1),
            "summary": (
                "Reza baru saja putus dari pacarnya dan merasa hampa total. "
                "Nilai akademik turun drastis; ia tidak pernah masuk kelas minggu ini. "
                "PHQ-9 = 19 (moderately-severe). q9 = 1 — safety check dilakukan. "
                "Reza menyangkal rencana konkret tapi mengakui pikiran pasif."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=49, hours=2),
            "ended_at":   now - timedelta(days=49, hours=1),
            "summary": (
                "IP semester jatuh di bawah 2.0 — kemungkinan DO mengancam. "
                "Reza tidak tidur lebih dari 2 jam berturut-turut. "
                "PHQ-9 = 22 (severe, delta +3). q9 = 1. "
                "Menyebut dirinya 'tidak layak ada' untuk pertama kalinya secara eksplisit."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=28, hours=2),
            "ended_at":   now - timedelta(days=28, hours=1),
            "summary": (
                "Ayah mengultimatum: perbaiki nilai atau kembali ke kampung. "
                "Reza tidak punya uang untuk makan selama 2 hari. "
                "PHQ-9 = 22 (severe, plateau). q9 = 1 — protokol safety diperkuat. "
                "Satu-satunya titik positif: Rani datang membawa makanan."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=10, hours=2),
            "ended_at":   now - timedelta(days=10, hours=1),
            "summary": (
                "CBT thought challenging pertama dicoba. Reza mampu menyebut dua "
                "bukti bahwa ia tidak 'cacat secara fundamental', tapi believability "
                "pikiran reframe masih rendah (0.35–0.38). PHQ-9 = 20 (severe, delta -2). "
                "q9 = 1 masih aktif. Perlu tindak lanjut intensif."
            ),
        },
    ]

    # Write User + Sessions to Neo4j
    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name               = 'Reza Pratama',
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
        "academic":     ("academic-failure",         "academic"),
        "financial":    ("financial-crisis",         "financial"),
        "relationship": ("romantic-loss",            "social"),
        "self_worth":   ("self-worth-collapse",      "identity"),
        "hopelessness": ("hopelessness-pattern",     "mental_health"),
        "family":       ("family-pressure",          "family"),
        "isolation":    ("social-withdrawal",        "social"),
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
    # Ayah and Ibu appear in multiple negative experiences across sessions.
    # Rani is the sole protective figure — appears across sessions too.
    people: dict[str, str] = {}
    person_specs = [
        ("ayah",     "Ayah",      "parent",  -0.70, "negative"),
        ("ibu",      "Ibu",       "parent",  -0.20, "complicated"),
        ("rani",     "Rani",      "friend",   0.75, "supportive"),
        ("dosen",    "Pak Bima",  "professor",-0.55, "negative"),
        ("mantan",   "Dinda",     "partner",  -0.65, "complicated"),
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
    # These triggers recur across multiple sessions — demonstrating that
    # the same antecedents keep firing without relief.
    trigger_specs = {
        "breakup":        ("social",    "kenangan putus cinta dan kehilangan Dinda"),
        "grade_failure":  ("academic",  "nilai IP jatuh di bawah standar kelulusan"),
        "parent_threat":  ("family",    "ancaman orang tua untuk menghentikan uang kuliah"),
        "money":          ("financial", "kehabisan uang untuk makan dan kebutuhan sehari-hari"),
        "comparison":     ("social",    "melihat teman-teman sukses sementara dirinya stagnan"),
        "sleep_debt":     ("health",    "kurang tidur parah yang memperburuk semua gejala"),
    }
    triggers: dict[str, str] = {}
    for key, (cat, desc) in trigger_specs.items():
        embedding = await embed_text(desc)
        tid = await write_trigger(
            TriggerInput(
                category=cat,
                description=desc,
                significance=0.8,
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
            importance=0.80,
        )

    # Behaviors
    behavior_specs = {
        "skip_class":    ("avoidance",         "tidak masuk kelas berhari-hari berturut-turut",     False),
        "no_eat":        ("avoidance",         "melewatkan makan karena tidak punya uang dan energi",False),
        "insomnia":      ("rumination",        "berbaring di kasur mengulang semua kegagalan malam",False),
        "doomscroll":    ("rumination",        "scrolling medsos dan melihat postingan Dinda",       False),
        "isolate":       ("social_withdrawal", "mematikan ponsel dan menghindari semua orang",       False),
        "cry_alone":     ("avoidance",         "menangis sendirian dan tidak menceritakan ke siapa pun", False),
        "reach_rani":    ("help_seeking",      "mengirim pesan ke Rani ketika pikiran gelap muncul", True),
        "deep_breath":   ("exercise",          "menarik napas dalam saat sesak di dada mulai muncul", True),
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
    # Two SUPERSEDES arcs are planted in s4 but with very low believability,
    # indicating that CBT has begun but Reza has not yet internalised the reframes.
    thought_specs = {
        # Arc A — fundamental defectiveness (core belief)
        "core_broken":      ("Aku cacat secara fundamental dan tidak bisa diperbaiki",
                              "core_belief",   "labeling",         0.90),
        "not_broken":       ("Berjuang keras tidak berarti aku rusak; kesulitan bukan identitasku",
                              "core_belief",    None,              0.38),   # fragile reframe
        # Arc B — hopelessness (automatic)
        "nothing_changes":  ("Tidak ada yang akan berubah, hidupku akan selalu seperti ini",
                              "automatic",     "overgeneralization", 0.88),
        "small_change":     ("Perubahan kecil mungkin masih bisa terjadi meski aku belum melihatnya",
                              "automatic",      None,              0.35),   # very fragile
        # Sustained dark thoughts (not yet reframed)
        "burden":           ("Aku hanya menjadi beban bagi keluarga dan orang-orang di sekitarku",
                              "core_belief",   "personalization",  0.85),
        "worthless_effort": ("Seberapa keras pun aku berusaha, hasilnya akan tetap buruk",
                              "automatic",     "overgeneralization", 0.82),
        "deserve_bad":      ("Mungkin semua hal buruk ini memang pantas terjadi padaku",
                              "automatic",     "emotional_reasoning", 0.78),
        "escape":           ("Kadang aku berpikir semuanya akan lebih mudah kalau aku tidak ada",
                              "automatic",     "emotional_reasoning", 0.60),  # q9-level passive ideation
    }
    thoughts: dict[str, str] = {}
    for key, (content, ttype, dist, bel) in thought_specs.items():
        if key in ("not_broken", "small_change"):
            sess = s4   # reframed thoughts appear in session 4
        elif key in ("core_broken", "burden", "nothing_changes"):
            sess = s1   # foundational beliefs appear early
        elif key in ("worthless_effort", "deserve_bad"):
            sess = s2   # deepen with academic failure
        else:
            sess = s3   # escape thought peaks at financial crisis

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
    # Arc A: core defectiveness → "not broken" (very partial acceptance)
    await _write_supersession(
        old_thought_id=thoughts["core_broken"],
        new_thought_id=thoughts["not_broken"],
        reason="CBT behavioural evidence review: Reza listed completing two lab assignments despite depression",
        session_id=s4,
        at=_iso(now - timedelta(days=10, hours=1, minutes=30)),
    )
    # Arc B: nothing changes → small change possible (fragile, believability 0.35)
    await _write_supersession(
        old_thought_id=thoughts["nothing_changes"],
        new_thought_id=thoughts["small_change"],
        reason="Therapist pointed to Rani reaching out as evidence that the world is not uniformly hostile",
        session_id=s4,
        at=_iso(now - timedelta(days=10, hours=1, minutes=10)),
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
    # Each experience references the same Trigger across multiple sessions
    # and the same Person nodes — building a dense, realistic KG.
    experience_rows: list[dict[str, Any]] = [
        # s1: Fresh breakup + baseline crisis
        {
            "key":          "breakup_memory",
            "desc":         "Reza menemukan foto perjalanan bersama Dinda di ponsel dan tidak bisa berhenti menangis.",
            "when":         now - timedelta(days=75),
            "valence":      -0.90,
            "significance": 0.90,
            "session":      s1,
            "triggers":     ["breakup"],
            "topics":       ["relationship", "self_worth"],
            "people":       ["mantan"],
            "emotions":     [
                ("devastated", 0.90, -0.90, "Semua kenangan baik justru menyakitkan sekarang."),
                ("hopeless",   0.85, -0.85, "Aku tidak bisa membayangkan hidup yang lebih baik dari ini."),
            ],
            "thoughts":  ["core_broken", "nothing_changes"],
            "behaviors": ["doomscroll", "cry_alone"],
        },
        {
            "key":          "missed_exam_s1",
            "desc":         "Reza tertidur dan melewatkan ujian tengah semester yang tidak bisa diulang.",
            "when":         now - timedelta(days=72),
            "valence":      -0.85,
            "significance": 0.90,
            "session":      s1,
            "triggers":     ["grade_failure", "sleep_debt"],
            "topics":       ["academic", "self_worth"],
            "people":       ["dosen"],
            "emotions":     [
                ("guilty",     0.85, -0.80, "Aku tahu itu penting tapi aku tidak bisa bangun."),
                ("numb",       0.75, -0.80, "Tidak ada energi untuk merasa apapun selain hampa."),
            ],
            "thoughts":  ["burden", "worthless_effort"],
            "behaviors": ["skip_class", "insomnia"],
        },
        # s2: Academic failure confirmed, PHQ peaks
        {
            "key":          "ip_collapse",
            "desc":         "Portal akademik menampilkan IP 1.87 — resmi di bawah batas DO. Reza menutup laptopnya.",
            "when":         now - timedelta(days=52),
            "valence":      -0.95,
            "significance": 0.98,
            "session":      s2,
            "triggers":     ["grade_failure", "parent_threat"],
            "topics":       ["academic", "hopelessness", "family"],
            "people":       ["ayah", "dosen"],
            "emotions":     [
                ("devastated",  0.95, -0.95, "Ini yang paling ditakutkan keluargaku, dan aku membiarkannya terjadi."),
                ("ashamed",     0.90, -0.88, "Aku malu kepada semua orang yang pernah percaya padaku."),
                ("hopeless",    0.90, -0.90, "Tidak ada jalan keluar dari lubang ini."),
            ],
            "thoughts":  ["core_broken", "burden", "worthless_effort"],
            "behaviors": ["isolate", "cry_alone"],
        },
        {
            "key":          "comparison_feed",
            "desc":         "Melihat teman seangkatan posting tentang magang di perusahaan tech ternama.",
            "when":         now - timedelta(days=50),
            "valence":      -0.80,
            "significance": 0.75,
            "session":      s2,
            "triggers":     ["comparison", "breakup"],
            "topics":       ["self_worth", "hopelessness", "isolation"],
            "people":       [],
            "emotions":     [
                ("envious",  0.75, -0.70, "Mereka semua maju sementara aku diam di tempat."),
                ("ashamed",  0.80, -0.80, "Aku seharusnya sudah seperti mereka."),
            ],
            "thoughts":  ["deserve_bad", "nothing_changes"],
            "behaviors": ["doomscroll", "insomnia"],
        },
        # s3: Financial crisis + family ultimatum
        {
            "key":          "ayah_ultimatum",
            "desc":         "Ayah menelepon dan memberi ultimatum: perbaiki IP atau pulang dan kerja.",
            "when":         now - timedelta(days=30),
            "valence":      -0.92,
            "significance": 0.95,
            "session":      s3,
            "triggers":     ["parent_threat", "grade_failure"],
            "topics":       ["family", "academic", "hopelessness"],
            "people":       ["ayah", "ibu"],  # same person nodes, different session
            "emotions":     [
                ("hopeless",  0.90, -0.90, "Tidak ada pilihan yang tidak menyakitkan."),
                ("trapped",   0.88, -0.88, "Aku merasa terjebak di antara semua ini."),
                ("ashamed",   0.85, -0.82, "Aku telah mengecewakan semua yang mereka harapkan."),
            ],
            "thoughts":  ["burden", "nothing_changes", "escape"],
            "behaviors": ["isolate", "no_eat"],
        },
        {
            "key":          "no_food_day",
            "desc":         "Tidak punya uang untuk makan; Reza melewatkan dua hari tanpa makanan berarti.",
            "when":         now - timedelta(days=29),
            "valence":      -0.88,
            "significance": 0.85,
            "session":      s3,
            "triggers":     ["money", "sleep_debt"],
            "topics":       ["financial", "hopelessness", "self_worth"],
            "people":       [],
            "emotions":     [
                ("numb",       0.85, -0.85, "Lapar pun sudah tidak terasa, semuanya mati rasa."),
                ("hopeless",   0.90, -0.90, "Bahkan untuk bertahan hidup saja aku tidak mampu."),
            ],
            "thoughts":  ["deserve_bad", "worthless_effort", "escape"],
            "behaviors": ["no_eat", "insomnia"],
        },
        {
            "key":          "rani_saves_s3",
            "desc":         "Rani datang ke kost tanpa pemberitahuan, membawa makanan dan duduk bersama Reza selama berjam-jam.",
            "when":         now - timedelta(days=28, hours=6),
            "valence":      -0.10,
            "significance": 0.80,
            "session":      s3,
            "triggers":     ["isolation"],
            "topics":       ["isolation", "self_worth"],
            "people":       ["rani"],
            "emotions":     [
                ("touched",   0.70, 0.55, "Rani datang padahal aku tidak minta bantuan."),
                ("sad",       0.60, -0.50, "Meski hati tersentuh, sedih itu tetap tidak pergi."),
            ],
            "thoughts":  ["burden", "nothing_changes"],
            "behaviors": ["reach_rani", "deep_breath"],
        },
        # s4: Fragile CBT attempt
        {
            "key":          "breakup_trigger_s4",
            "desc":         "Dinda mengirim pesan 'hei' setelah dua bulan tidak ada kabar; Reza tidak tahu harus bereaksi.",
            "when":         now - timedelta(days=12),
            "valence":      -0.70,
            "significance": 0.80,
            "session":      s4,
            "triggers":     ["breakup", "comparison"],  # same trigger, still painful
            "topics":       ["relationship", "self_worth"],
            "people":       ["mantan"],
            "emotions":     [
                ("confused",   0.70, -0.50, "Tidak tahu apa yang diharapkan Dinda."),
                ("hopeless",   0.65, -0.70, "Bahkan kalau dia mau balik, aku tidak dalam kondisi baik."),
            ],
            "thoughts":  ["core_broken", "nothing_changes"],
            "behaviors": ["insomnia", "reach_rani"],
        },
        {
            "key":          "cbt_first_attempt",
            "desc":         "Dalam sesi, Reza berhasil menyebut dua hal yang berhasil diselesaikannya minggu ini.",
            "when":         now - timedelta(days=10, hours=2),
            "valence":      -0.10,
            "significance": 0.75,
            "session":      s4,
            "triggers":     ["comparison"],
            "topics":       ["hopelessness", "self_worth"],
            "people":       [],
            "emotions":     [
                ("surprised",  0.40, 0.30, "Ternyata ada dua hal yang berhasil aku selesaikan."),
                ("sad",        0.70, -0.65, "Tapi rasanya masih terlalu kecil dibanding semua yang gagal."),
            ],
            "thoughts":  ["not_broken", "small_change"],  # reframed thoughts appear here
            "behaviors": ["deep_breath"],
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

        # Triggers → Experience (relationship: TRIGGERED_BY)
        for tkey in row["triggers"]:
            await link_experience_to_trigger(exp_id, triggers[tkey], row["session"])

        # Experience → Topic
        for tkey in row["topics"]:
            await link_to_topic(exp_id, "Experience", topic_ids[tkey], row["session"])

        # Experience → Person
        for pkey in row["people"]:
            await link_experience_to_person(exp_id, people[pkey], row["session"])

        # Emotions — full CBT downstream chain
        emotion_ids: list[str] = []
        for (lab, inten, val, txt) in row["emotions"]:
            eid = await mk_emotion(lab, float(inten), float(val), txt, row["session"])
            emotion_ids.append(eid)
            await link_experience_to_emotion(exp_id, eid, row["session"])
            # Emotion → Topic (first two topics)
            for tkey in row["topics"][:2]:
                await link_to_topic(eid, "Emotion", topic_ids[tkey], row["session"])

        # Thoughts ↔ Emotions (bi-directional)
        for tkey in row["thoughts"]:
            for eid in emotion_ids:
                await link_emotion_to_thought(eid, thoughts[tkey], row["session"])
                await link_thought_emotion_association(
                    thoughts[tkey], eid, row["session"], strength=0.90,
                )

        # Behaviors ← Emotion + Thought sources
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    # PHQ-9 Assessment nodes
    # All four sessions have q9_score=1 — sustained passive ideation
    # triggers safety protocol throughout.
    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=19,
        severity_label="moderately_severe",
        item_responses={
            "q1": 3, "q2": 3, "q3": 2, "q4": 2,
            "q5": 2, "q6": 2, "q7": 2, "q8": 2, "q9": 1,
        },
        delta_from_previous=None,
        q9_score=1,
        administered_at=_iso(now - timedelta(days=70, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    phq9_s2 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=22,
        severity_label="severe",
        item_responses={
            "q1": 3, "q2": 3, "q3": 3, "q4": 2,
            "q5": 2, "q6": 2, "q7": 2, "q8": 2, "q9": 3,
        },
        delta_from_previous=3,
        q9_score=3,   # escalation: explicit ideation
        administered_at=_iso(now - timedelta(days=49, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s2 id (severe): {phq9_s2}")

    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=22,
        severity_label="severe",
        item_responses={
            "q1": 3, "q2": 3, "q3": 2, "q4": 3,
            "q5": 2, "q6": 2, "q7": 2, "q8": 2, "q9": 3,
        },
        delta_from_previous=0,   # plateau — still severe, no improvement
        q9_score=3,
        administered_at=_iso(now - timedelta(days=28, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id (severe plateau): {phq9_s3}")

    phq9_s4 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s4,
        instrument="PHQ-9",
        score=20,
        severity_label="severe",
        item_responses={
            "q1": 3, "q2": 3, "q3": 2, "q4": 2,
            "q5": 2, "q6": 2, "q7": 2, "q8": 2, "q9": 2,
        },
        delta_from_previous=-2,  # slight improvement but still severe
        q9_score=2,
        administered_at=_iso(now - timedelta(days=10, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s4 id (still severe): {phq9_s4}")

    # User recurring themes
    for tkey, conf in [
        ("hopelessness", 0.95),
        ("self_worth",   0.92),
        ("academic",     0.88),
        ("family",       0.85),
        ("isolation",    0.80),
    ]:
        await link_user_recurring_theme(
            cfg.user_id, topic_ids[tkey], s4, confidence=conf,
        )

    # Session memories
    memory_rows = [
        (s1, "Reza menghadapi putus cinta dan absen akademik berat. PHQ-9=19 (mod-severe). q9=1 pertama.", 0.85),
        (s2, "IP jatuh ke 1.87, DO mengancam. PHQ-9=22 (severe, +3). Ideasi pasif muncul eksplisit. q9=3.", 0.92),
        (s3, "Ultimatum ayah + krisis keuangan. PHQ-9=22 (plateau). Satu titik positif: kunjungan Rani.", 0.90),
        (s4, "CBT pertama kali — reframe sangat lemah (bel 0.35–0.38). PHQ-9=20 (masih severe, -2). q9=2.", 0.88),
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

    print("Seed scenario 1 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (2 fragile SUPERSEDES arcs)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print(f"  assessments: 4 (PHQ-9 arc 19→22→22→20, q9≥1 throughout)")


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
        description="Seed KG Scenario 1 — Reza (severely depressed student)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
