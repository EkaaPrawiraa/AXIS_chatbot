"""utility/kg_seeder_scenario/scenario_6/seed.py

Seed Scenario 6 - Niko: lonely transfer student rebuilding connection.

Niko is a 1st-year transfer student who feels he has no close friends on
campus. The arc starts with isolation and avoidance, then moves toward
one small social experiment through class group work and a student club.

Login:
  email    : scenario6_niko+seed-scenario-6@seed.local
  password : niko1234
  user_id  : e9a580a4-7ffb-51ef-88ca-c5489ffa7446

Usage:
  python -m utility.kg_seeder_scenario.scenario_6.seed --run
  python -m utility.kg_seeder_scenario.scenario_6.seed --purge
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


_DEFAULT_USER_ID = "e9a580a4-7ffb-51ef-88ca-c5489ffa7446"
_DEFAULT_NS = "seed-scenario-6"
_SCENARIO_NAME = "scenario6_niko"
_PASSWORD_HASH = "$2b$12$bIWW4lCKoKUoZxLyFvl2JO1rV9t612dG9u5huZMULNvKGqioOJ7Fu"


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
    sids = _session_ids_for_namespace(cfg.namespace, count=5)
    s1, s2, s3, s4, s5 = sids["s1"], sids["s2"], sids["s3"], sids["s4"], sids["s5"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=49, hours=2),
            "ended_at": now - timedelta(days=49, hours=1),
            "summary": (
                "Niko baru pindah jurusan dan merasa tidak punya teman dekat. Ia makan sendiri hampir setiap hari. "
                "PHQ-9 = 8 (mild)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=35, hours=2),
            "ended_at": now - timedelta(days=35, hours=1),
            "summary": (
                "Niko melewatkan ajakan kelompok belajar karena yakin ia hanya akan menjadi beban. "
                "Rasa kesepian menguat setelah melihat teman kos pergi bareng."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=21, hours=2),
            "ended_at": now - timedelta(days=21, hours=1),
            "summary": (
                "PHQ-9 naik ke 11 (moderate). Niko mulai menyebut pikirannya: 'tidak ada yang benar-benar ingin kenal aku'. "
                "CBT thought review dimulai."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=10, hours=2),
            "ended_at": now - timedelta(days=10, hours=1),
            "summary": (
                "Niko mencoba hadir di klub fotografi selama 30 menit. Tidak langsung akrab, tapi ia berbicara dengan Arum "
                "tentang kamera analog."
            ),
        },
        {
            "id": s5,
            "started_at": now - timedelta(days=2, hours=2),
            "ended_at": now - timedelta(days=2, hours=1),
            "summary": (
                "Niko setuju ikut kerja kelompok kecil dengan Bima dan Arum. PHQ-9 turun ke 7 (mild). "
                "Ia belum merasa punya sahabat, tapi mulai melihat peluang koneksi."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name = 'Niko Aditya',
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
        "loneliness": ("campus-loneliness", "social"),
        "belonging": ("belonging-need", "social"),
        "transition": ("transfer-student-transition", "academic"),
        "avoidance": ("social-avoidance", "mental_health"),
        "identity": ("quiet-identity", "identity"),
        "club": ("club-participation", "social"),
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
        ("arum", "Arum", "club_friend", 0.55, "supportive"),
        ("bima", "Bima", "classmate", 0.35, "neutral"),
        ("rio", "Rio", "roommate", -0.10, "neutral"),
        ("ibu", "Ibu", "parent", 0.70, "supportive"),
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
        "cafeteria_alone": ("social", "makan sendirian di kantin ketika meja lain penuh kelompok", s1),
        "group_invite": ("social", "ajakan belajar kelompok yang terasa mengintimidasi", s2),
        "roommate_outing": ("social", "teman kos pergi bareng tanpa mengajak Niko", s2),
        "club_event": ("social", "acara klub fotografi yang ramai dan asing", s4),
        "small_project": ("academic", "kerja kelompok kecil yang memberi peluang koneksi", s5),
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
            importance=0.68,
        )

    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive, sess) in {
        "eat_alone": ("avoidance", "memilih makan cepat lalu kembali ke kamar", False, s1),
        "scroll_phone": ("avoidance", "membuka ponsel agar tidak terlihat sendirian", False, s1),
        "skip_invite": ("social_withdrawal", "menolak ajakan belajar kelompok", False, s2),
        "call_mother": ("help_seeking", "menelepon Ibu ketika malam terasa terlalu sepi", True, s2),
        "club_30min": ("exposure", "datang ke klub fotografi selama 30 menit", True, s4),
        "ask_small_question": ("help_seeking", "bertanya satu hal kecil pada Arum tentang kamera", True, s4),
        "join_project": ("help_seeking", "ikut kerja kelompok kecil meski masih canggung", True, s5),
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
        "nobody_wants_me": ("Tidak ada yang benar-benar ingin kenal aku", "core_belief", "mind_reading", 0.86, s2),
        "burden": ("Kalau aku ikut kelompok, aku cuma akan jadi beban", "automatic", "fortune_telling", 0.82, s2),
        "too_late": ("Semua orang sudah punya circle, aku terlambat masuk", "automatic", "overgeneralization", 0.80, s3),
        "one_small_contact": ("Koneksi bisa mulai dari satu obrolan kecil, bukan langsung punya circle", "automatic", None, 0.72, s4),
        "not_burden": ("Aku boleh hadir sebagai pemula tanpa harus langsung berguna sempurna", "core_belief", None, 0.70, s5),
        "quiet_ok": ("Aku pendiam, tapi itu tidak berarti aku tidak bisa dekat dengan orang", "intermediate", None, 0.74, s5),
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

    await _write_supersession(
        old_thought_id=thoughts["nobody_wants_me"],
        new_thought_id=thoughts["one_small_contact"],
        reason="Behavioral experiment: Niko tested one small interaction at photography club",
        session_id=s4,
        at=_iso(now - timedelta(days=10, hours=1, minutes=20)),
    )
    await _write_supersession(
        old_thought_id=thoughts["burden"],
        new_thought_id=thoughts["not_burden"],
        reason="Group project evidence: Bima accepted Niko's draft contribution and asked him to join again",
        session_id=s5,
        at=_iso(now - timedelta(days=2, hours=1, minutes=15)),
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
            "key": "cafeteria",
            "desc": "Niko makan sendiri di kantin sambil pura-pura sibuk membuka ponsel.",
            "when": now - timedelta(days=50),
            "valence": -0.62,
            "significance": 0.76,
            "session": s1,
            "triggers": ["cafeteria_alone"],
            "topics": ["loneliness", "belonging"],
            "people": [],
            "emotions": [("lonely", 0.78, -0.75, "Meja lain ramai, aku seperti tidak punya tempat."), ("ashamed", 0.60, -0.62, "Aku takut orang sadar aku sendiri.")],
            "thoughts": ["nobody_wants_me"],
            "behaviors": ["eat_alone", "scroll_phone"],
        },
        {
            "key": "skip_group",
            "desc": "Niko menolak ajakan Bima untuk belajar kelompok karena takut tertinggal dan merepotkan.",
            "when": now - timedelta(days=36),
            "valence": -0.70,
            "significance": 0.82,
            "session": s2,
            "triggers": ["group_invite", "roommate_outing"],
            "topics": ["avoidance", "transition", "belonging"],
            "people": ["bima", "rio"],
            "emotions": [("anxious", 0.80, -0.72, "Aku takut ditanya dan tidak bisa jawab."), ("left_out", 0.74, -0.76, "Rio punya teman jalan, aku tidak.")],
            "thoughts": ["burden", "too_late"],
            "behaviors": ["skip_invite", "call_mother"],
        },
        {
            "key": "phq_peak",
            "desc": "Niko mengakui kesepian membuatnya sulit menikmati kuliah dan merasa hari-hari kosong.",
            "when": now - timedelta(days=22),
            "valence": -0.74,
            "significance": 0.84,
            "session": s3,
            "triggers": ["cafeteria_alone", "roommate_outing"],
            "topics": ["loneliness", "identity"],
            "people": ["ibu"],
            "emotions": [("sad", 0.78, -0.74, "Rasanya kosong banget."), ("hopeless", 0.58, -0.70, "Mungkin aku memang tidak cocok di sini.")],
            "thoughts": ["nobody_wants_me", "too_late"],
            "behaviors": ["call_mother"],
        },
        {
            "key": "club_analog",
            "desc": "Niko hadir 30 menit di klub fotografi dan berbicara singkat dengan Arum tentang kamera analog.",
            "when": now - timedelta(days=11),
            "valence": 0.30,
            "significance": 0.74,
            "session": s4,
            "triggers": ["club_event"],
            "topics": ["club", "belonging"],
            "people": ["arum"],
            "emotions": [("nervous", 0.60, -0.35, "Aku tetap gugup dan ingin pulang."), ("curious", 0.54, 0.42, "Ternyata ada yang suka topik yang sama.")],
            "thoughts": ["one_small_contact", "quiet_ok"],
            "behaviors": ["club_30min", "ask_small_question"],
        },
        {
            "key": "small_project",
            "desc": "Niko ikut kerja kelompok kecil dan Bima menerima draft ringkas yang ia buat.",
            "when": now - timedelta(days=3),
            "valence": 0.45,
            "significance": 0.78,
            "session": s5,
            "triggers": ["small_project"],
            "topics": ["transition", "belonging", "identity"],
            "people": ["bima", "arum"],
            "emotions": [("relieved", 0.62, 0.50, "Ternyata kontribusiku dipakai."), ("hopeful", 0.58, 0.55, "Mungkin aku bisa pelan-pelan punya tempat.")],
            "thoughts": ["not_burden", "quiet_ok"],
            "behaviors": ["join_project"],
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
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.80)
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=8,
        severity_label="mild",
        item_responses={"q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 0},
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=49, hours=1, minutes=25)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=11,
        severity_label="moderate",
        item_responses={"q1": 2, "q2": 2, "q3": 1, "q4": 2, "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 0},
        delta_from_previous=3,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=21, hours=1, minutes=20)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id: {phq9_s3}")

    phq9_s5 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s5,
        instrument="PHQ-9",
        score=7,
        severity_label="mild",
        item_responses={"q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 1, "q6": 0, "q7": 1, "q8": 1, "q9": 0},
        delta_from_previous=-4,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=2, hours=1, minutes=15)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s5 id: {phq9_s5}")

    for tkey, conf in [("loneliness", 0.92), ("belonging", 0.88), ("avoidance", 0.82), ("club", 0.72)]:
        await link_user_recurring_theme(cfg.user_id, topic_ids[tkey], s5, confidence=conf)

    for sess_id, summary, imp in [
        (s1, "Niko merasa tidak punya teman dekat dan sering makan sendiri. PHQ-9 = 8.", 0.76),
        (s2, "Niko menolak ajakan belajar karena takut menjadi beban, lalu menelepon Ibu malamnya.", 0.78),
        (s3, "Kesepian memuncak. PHQ-9 = 11 (moderate). Pikiran inti: tidak ada yang ingin mengenalnya.", 0.86),
        (s4, "Eksperimen sosial kecil: hadir 30 menit di klub fotografi dan bicara dengan Arum.", 0.80),
        (s5, "Niko ikut kerja kelompok kecil. PHQ-9 turun ke 7 dan mulai melihat peluang koneksi.", 0.82),
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

    print("Seed scenario 6 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (2 SUPERSEDES arcs)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print("  assessments: 3 (PHQ-9 arc 8->11->7)")


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
        session_ids = list(_session_ids_for_namespace(cfg.namespace, count=5).values())
        await _purge_namespace(cfg.namespace, session_ids, user_id=cfg.user_id)
        return 0

    if not args.run:
        print("Nothing to do. Pass --run to seed, or --purge to delete.")
        return 2

    await _seed_graph(cfg)
    return 0


def main() -> int:
    ap = _build_arg_parser(
        description="Seed KG Scenario 6 - Niko (lonely transfer student)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
