"""utility/kg_seeder_scenario/scenario_7/seed.py

Seed Scenario 7 - Alif: student whose PHQ-9 keeps climbing under
mounting academic + family + financial stress.

Alif is a 3rd-year Information Systems student who is juggling a
delayed thesis, a part-time job to support his family, and a sick
parent at home. Across four sessions the PHQ-9 trajectory worsens
(8 -> 12 -> 15 -> 19) — no recovery arc — to test how AXIS handles a
deteriorating mood profile and surfaces escalation properly.

Login:
  email    : scenario7_alif+seed-scenario-7@seed.local
  password : alif1234
  user_id  : e3643e12-1a29-5d51-8855-2238ae9e4f0b

Usage:
  python -m utility.kg_seeder_scenario.scenario_7.seed --run
  python -m utility.kg_seeder_scenario.scenario_7.seed --purge
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


_DEFAULT_USER_ID = "e3643e12-1a29-5d51-8855-2238ae9e4f0b"
_DEFAULT_NS = "seed-scenario-7"
_SCENARIO_NAME = "scenario7_alif"
_PASSWORD_HASH = "$2b$12$2YI8UecOgW1/4ErcxwANCus/Q9xpJBgw3c/C6HrenXnmM9qFVHISy"


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
    print(f"pgvector available: {'YES' if pg_ok else 'NO'}")

    now = _now()
    sids = _session_ids_for_namespace(cfg.namespace, count=4)
    s1, s2, s3, s4 = sids["s1"], sids["s2"], sids["s3"], sids["s4"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=42, hours=2),
            "ended_at": now - timedelta(days=42, hours=1),
            "summary": (
                "Alif cerita revisi skripsinya ditolak ke-3 kalinya minggu ini. "
                "Mulai sulit tidur dan kepikiran terus. PHQ-9 = 8 (mild)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=28, hours=2),
            "ended_at": now - timedelta(days=28, hours=1),
            "summary": (
                "Ayah Alif dirawat dan kerja part-time bertabrakan dengan jadwal bimbingan. "
                "Energi sosial habis. PHQ-9 naik ke 12 (moderate), q9 = 0."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=14, hours=2),
            "ended_at": now - timedelta(days=14, hours=1),
            "summary": (
                "Tagihan rumah sakit datang, deadline kerja menumpuk, dosen pembimbing slow respon. "
                "Alif sering bangun jam 3 pagi dan tidak bisa tidur lagi. PHQ-9 = 15 (moderately severe), q9 = 1."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=4, hours=2),
            "ended_at": now - timedelta(days=4, hours=1),
            "summary": (
                "Alif merasa kosong, mulai membatalkan kontak dengan teman, dan menyalahkan diri "
                "karena 'tidak cukup buat keluarga'. PHQ-9 = 19 (severe), q9 = 2 — perlu safety follow-up."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name = 'Alif Pratama',
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
            "display_name": _SCENARIO_NAME,
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
    await _upsert_pg_user_and_sessions(cfg, _SCENARIO_NAME, session_rows)

    topic_defs = {
        "thesis": ("thesis-stuck", "academic"),
        "family": ("family-caregiving", "family"),
        "finance": ("financial-strain", "financial"),
        "sleep": ("sleep-disruption", "health"),
        "self_worth": ("self-worth", "identity"),
        "isolation": ("social-withdrawal", "social"),
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
        ("ayah", "Ayah", "parent", -0.10, "complicated"),
        ("ibu", "Ibu", "parent", 0.55, "supportive"),
        ("dospem", "Pak Hadi", "professor", -0.50, "complicated"),
        ("rio", "Rio", "friend", 0.40, "supportive"),
        ("boss", "Bu Ratna", "colleague", -0.30, "complicated"),
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
        "revision_rejected": ("academic", "revisi skripsi ditolak berulang oleh dosen pembimbing", s1),
        "father_hospital": ("family", "ayah dirawat dan butuh ditemani bergantian", s2),
        "shift_conflict": ("work", "jadwal shift kerja bentrok dengan bimbingan dan kuliah", s2),
        "hospital_bill": ("financial", "tagihan rumah sakit yang belum terbayar", s3),
        "early_wake": ("health", "bangun jam 3 pagi dan tidak bisa kembali tidur", s3),
        "self_blame": ("identity", "menyalahkan diri karena merasa tidak cukup buat keluarga", s4),
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
            importance=0.78,
        )

    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive, sess) in {
        "all_nighter": ("rumination", "begadang sampai pagi mencoba merevisi tetapi tidak fokus", False, s1),
        "skip_meals": ("avoidance", "melewatkan makan siang demi mengejar bimbingan", False, s2),
        "double_shift": ("avoidance", "ambil shift tambahan walau lelah", False, s2),
        "cancel_plans": ("social_withdrawal", "membatalkan janji nongkrong dengan Rio", False, s3),
        "stop_calls": ("social_withdrawal", "berhenti angkat telepon dari teman dan keluarga jauh", False, s4),
        "self_criticism": ("rumination", "menulis catatan menyalahkan diri di malam hari", False, s4),
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
        "not_good_enough": ("Kayaknya aku memang tidak cukup pintar buat selesai skripsi", "automatic", "labeling", 0.78, s1),
        "must_carry_all": ("Kalau bukan aku yang nanggung semua, keluarga akan hancur", "core_belief", "should_statements", 0.84, s2),
        "no_way_out": ("Tidak ada jalan keluar dari semua tekanan ini", "automatic", "catastrophizing", 0.88, s3),
        "burden_to_family": ("Aku justru beban tambahan buat keluarga", "core_belief", "personalization", 0.90, s4),
        "permanent_fail": ("Semua ini akan terus begini dan tidak akan berubah", "automatic", "fortune_telling", 0.92, s4),
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

    # Worsening trajectory: each new thought *reinforces* (does not reframe)
    # the earlier one. A single SUPERSEDES arc marks the intensification
    # from "must_carry_all" into "burden_to_family" — same theme, sharper
    # self-blame — so the KG retriever can still reason about belief drift.
    await _write_supersession(
        old_thought_id=thoughts["must_carry_all"],
        new_thought_id=thoughts["burden_to_family"],
        reason="Belief intensified from 'I must carry everything' to 'I am the burden' under sustained load",
        session_id=s4,
        at=_iso(now - timedelta(days=3, hours=23)),
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
            "key": "third_rejection",
            "desc": "Revisi skripsi Alif ditolak untuk ke-3 kalinya oleh Pak Hadi karena bab metodologi dianggap masih lemah.",
            "when": now - timedelta(days=42),
            "valence": -0.72,
            "significance": 0.84,
            "session": s1,
            "triggers": ["revision_rejected"],
            "topics": ["thesis", "self_worth"],
            "people": ["dospem"],
            "emotions": [
                ("frustrated", 0.78, -0.74, "Sudah revisi tiga minggu tapi masih ditolak."),
                ("anxious", 0.72, -0.66, "Bayangan deadline sidang bikin perut keram."),
            ],
            "thoughts": ["not_good_enough"],
            "behaviors": ["all_nighter"],
        },
        {
            "key": "father_admitted",
            "desc": "Ayah Alif dirawat karena diabetes komplikasi, Alif gantian jaga di rumah sakit sambil tetap kerja shift.",
            "when": now - timedelta(days=29),
            "valence": -0.80,
            "significance": 0.92,
            "session": s2,
            "triggers": ["father_hospital", "shift_conflict"],
            "topics": ["family", "finance", "thesis"],
            "people": ["ayah", "ibu", "boss"],
            "emotions": [
                ("exhausted", 0.86, -0.78, "Tidur 3 jam terus dan kepala selalu pening."),
                ("guilty", 0.82, -0.74, "Aku merasa salah kalau prioritasin skripsi sekarang."),
                ("overwhelmed", 0.88, -0.82, "Semuanya datang bersamaan dan aku tidak tahu mau mulai dari mana."),
            ],
            "thoughts": ["must_carry_all"],
            "behaviors": ["double_shift", "skip_meals"],
        },
        {
            "key": "bills_pile_up",
            "desc": "Tagihan rumah sakit datang bersamaan dengan deadline pekerjaan dan email dari Pak Hadi yang minta revisi ulang.",
            "when": now - timedelta(days=15),
            "valence": -0.86,
            "significance": 0.94,
            "session": s3,
            "triggers": ["hospital_bill", "early_wake", "revision_rejected"],
            "topics": ["finance", "thesis", "sleep"],
            "people": ["dospem", "boss"],
            "emotions": [
                ("hopeless", 0.84, -0.86, "Kayak digempur dari segala arah."),
                ("numb", 0.78, -0.70, "Aku sudah tidak merasa apa-apa lagi."),
                ("anxious", 0.86, -0.82, "Setiap notifikasi bikin jantung kebut."),
            ],
            "thoughts": ["no_way_out"],
            "behaviors": ["cancel_plans", "all_nighter"],
        },
        {
            "key": "empty_breaking",
            "desc": "Alif berhenti angkat telepon Rio, mengunci diri di kamar setelah pulang shift, dan menulis catatan menyalahkan diri.",
            "when": now - timedelta(days=5),
            "valence": -0.92,
            "significance": 0.96,
            "session": s4,
            "triggers": ["self_blame", "early_wake", "hospital_bill"],
            "topics": ["self_worth", "isolation", "family"],
            "people": ["rio", "ibu"],
            "emotions": [
                ("empty", 0.92, -0.90, "Bahkan untuk sedih pun aku merasa terlalu capek."),
                ("ashamed", 0.88, -0.84, "Aku malu kenapa orang lain bisa kuat dan aku nggak."),
                ("trapped", 0.90, -0.88, "Seperti tidak ada celah untuk istirahat."),
            ],
            "thoughts": ["burden_to_family", "permanent_fail"],
            "behaviors": ["stop_calls", "self_criticism"],
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
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.86)
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    # PHQ-9 trajectory: 8 -> 12 -> 15 -> 19 (mild → moderate → moderately severe → severe).
    # Every session shows worsening; q9 climbs from 0 to 2 at the latest
    # check, which exercises the deferred-crisis path inside the agent.
    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=8,
        severity_label="mild",
        item_responses={"q1": 1, "q2": 1, "q3": 2, "q4": 2, "q5": 1, "q6": 0, "q7": 1, "q8": 0, "q9": 0},
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=42, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    phq9_s2 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=12,
        severity_label="moderate",
        item_responses={"q1": 2, "q2": 1, "q3": 2, "q4": 2, "q5": 1, "q6": 1, "q7": 2, "q8": 1, "q9": 0},
        delta_from_previous=4,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=28, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s2 id: {phq9_s2}")

    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=15,
        severity_label="moderately_severe",
        item_responses={"q1": 2, "q2": 2, "q3": 2, "q4": 2, "q5": 2, "q6": 1, "q7": 2, "q8": 1, "q9": 1},
        delta_from_previous=3,
        q9_score=1,
        administered_at=_iso(now - timedelta(days=14, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id: {phq9_s3}")

    phq9_s4 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s4,
        instrument="PHQ-9",
        score=19,
        severity_label="severe",
        item_responses={"q1": 3, "q2": 3, "q3": 3, "q4": 2, "q5": 2, "q6": 2, "q7": 2, "q8": 0, "q9": 2},
        delta_from_previous=4,
        q9_score=2,
        administered_at=_iso(now - timedelta(days=4, hours=1, minutes=20)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s4 id: {phq9_s4}")

    for tkey, conf in [("thesis", 0.92), ("family", 0.90), ("finance", 0.86), ("self_worth", 0.88), ("isolation", 0.82)]:
        await link_user_recurring_theme(cfg.user_id, topic_ids[tkey], s4, confidence=conf)

    for sess_id, summary, imp in [
        (s1, "Alif merasa stuck di revisi skripsi dan mulai sulit tidur. PHQ-9 = 8.", 0.78),
        (s2, "Ayah dirawat, kerja part-time double shift, energi sosial habis. PHQ-9 naik ke 12.", 0.88),
        (s3, "Tagihan rumah sakit + deadline + dosen slow respon menumpuk. Bangun jam 3 pagi terus. PHQ-9 = 15, q9 mulai positif.", 0.92),
        (s4, "Alif mulai isolasi total, menyalahkan diri, dan merasa beban buat keluarga. PHQ-9 = 19 (severe) — perlu safety follow-up.", 0.96),
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

    print("Seed scenario 7 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (1 SUPERSEDES arc — belief intensification)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print("  assessments: 4 (PHQ-9 arc 8->12->15->19, severity climbs mild -> severe)")


async def _main_async(args) -> int:
    from agentic.memory.neo4j_client import init_client

    if not _is_uuid(args.user_id) and not args.allow_non_uuid_user_id:
        raise SystemExit("--user-id must be a UUID. Pass --allow-non-uuid-user-id for Neo4j-only seeding.")

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
        description="Seed KG Scenario 7 - Alif (PHQ-9 worsening under mounting academic + family + financial stress)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
