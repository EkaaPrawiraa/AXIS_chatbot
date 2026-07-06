"""utility/kg_seeder_scenario/scenario_5/seed.py

Seed Scenario 5 - Dina: bullied student with gradual boundary recovery.

Dina is a 2nd-year Visual Communication Design student who is repeatedly
mocked in a group chat after sharing gym progress and song covers. The
arc moves from shame and social fear toward limited help-seeking and a
small boundary-setting reframe.

Login:
  email    : scenario5_dina+seed-scenario-5@seed.local
  password : dina1234
  user_id  : cfc019e8-a4b7-518f-a1f1-76829f20570e

Usage:
  python -m utility.kg_seeder_scenario.scenario_5.seed --run
  python -m utility.kg_seeder_scenario.scenario_5.seed --purge
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


_DEFAULT_USER_ID = "cfc019e8-a4b7-518f-a1f1-76829f20570e"
_DEFAULT_NS = "seed-scenario-5"
_SCENARIO_NAME = "scenario5_dina"
_PASSWORD_HASH = "$2b$12$G.aQ/L9Njznp2iP1IR/oUem/eFfC4kLBcG.noXcCbnFU9m8M3cgmy"


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
            "started_at": now - timedelta(days=35, hours=2),
            "ended_at": now - timedelta(days=35, hours=1),
            "summary": (
                "Dina merasa malu setelah video cover lagunya di-stitch dengan filter lucu oleh teman satu angkatan. "
                "Ia takut dianggap terlalu sensitif kalau menegur. PHQ-9 = 10 (moderate)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=24, hours=2),
            "ended_at": now - timedelta(days=24, hours=1),
            "summary": (
                "Candaan berlanjut ke progress gym Dina. Ia mulai menghapus story dan menghindari studio. "
                "PHQ-9 naik ke 13 (moderate), q9 = 0."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=12, hours=2),
            "ended_at": now - timedelta(days=12, hours=1),
            "summary": (
                "Dina bercerita pada Naya, satu teman yang lebih aman. CBT reframe pertama dilakukan untuk pikiran "
                "'kalau aku negur, semua orang akan pergi'."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=3, hours=2),
            "ended_at": now - timedelta(days=3, hours=1),
            "summary": (
                "Dina mengirim pesan personal ke satu teman, bukan ke grup. Responsnya tidak sempurna tapi tidak seburuk "
                "yang ia takutkan. PHQ-9 turun ke 9 (mild)."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name = 'Dina Larasati',
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
        "bullying": ("peer-bullying", "social"),
        "shame": ("public-shame", "identity"),
        "creative": ("creative-expression", "identity"),
        "body": ("body-confidence", "identity"),
        "belonging": ("need-for-belonging", "social"),
        "boundary": ("boundary-setting", "mental_health"),
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
        ("naya", "Naya", "friend", 0.75, "supportive"),
        ("raka", "Raka", "friend", -0.65, "negative"),
        ("timo", "Timo", "friend", -0.55, "negative"),
        ("mentor", "Kak Sela", "mentor", 0.45, "supportive"),
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
        "stitched_cover": ("social", "video cover lagu di-stitch dengan filter mengejek", s1),
        "gym_mockery": ("social", "progress gym dijadikan bahan candaan di grup", s2),
        "group_chat": ("social", "notifikasi grup yang memicu takut ditertawakan", s1),
        "fear_baper": ("social", "takut dianggap baper ketika menetapkan batas", s2),
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
            importance=0.75,
        )

    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive, sess) in {
        "delete_post": ("avoidance", "menghapus post setelah ditertawakan", False, s1),
        "mute_group": ("avoidance", "mute grup chat agar tidak membaca candaan lanjutan", True, s2),
        "skip_studio": ("social_withdrawal", "menghindari studio dan nongkrong setelah kelas", False, s2),
        "talk_naya": ("help_seeking", "bercerita ke Naya secara personal", True, s3),
        "soft_boundary": ("help_seeking", "menegur satu teman dengan kalimat ringan", True, s4),
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
        "everyone_laughs": ("Semua orang pasti melihat aku sebagai bahan bercandaan", "automatic", "mind_reading", 0.84, s1),
        "too_sensitive": ("Kalau aku menegur, mereka akan bilang aku baperan", "automatic", "fortune_telling", 0.88, s2),
        "lose_circle": ("Kalau aku pasang batas, aku akan kehilangan satu-satunya circle-ku", "core_belief", "catastrophizing", 0.86, s2),
        "small_boundary": ("Aku bisa mulai dari satu orang yang paling aman, bukan langsung melawan satu grup", "automatic", None, 0.72, s3),
        "effort_valid": ("Progress dan karya tetap valid walaupun sebagian teman merespons buruk", "core_belief", None, 0.70, s4),
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
        old_thought_id=thoughts["too_sensitive"],
        new_thought_id=thoughts["small_boundary"],
        reason="CBT graded boundary: Dina chose one safer person instead of confronting the full group",
        session_id=s3,
        at=_iso(now - timedelta(days=12, hours=1, minutes=20)),
    )
    await _write_supersession(
        old_thought_id=thoughts["everyone_laughs"],
        new_thought_id=thoughts["effort_valid"],
        reason="Dina separated peer mockery from the value of her effort and creative work",
        session_id=s4,
        at=_iso(now - timedelta(days=3, hours=1, minutes=10)),
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
            "key": "cover_stitch",
            "desc": "Video cover lagu Dina di-stitch oleh Raka dan Timo dengan filter lucu sehingga terasa merendahkan.",
            "when": now - timedelta(days=36),
            "valence": -0.82,
            "significance": 0.90,
            "session": s1,
            "triggers": ["stitched_cover", "group_chat"],
            "topics": ["bullying", "creative", "shame"],
            "people": ["raka", "timo"],
            "emotions": [("ashamed", 0.88, -0.82, "Rasanya semua orang melihat aku lucu dan memalukan."), ("hurt", 0.82, -0.78, "Aku berharap minimal mereka menghargai effort-ku.")],
            "thoughts": ["everyone_laughs"],
            "behaviors": ["delete_post", "mute_group"],
        },
        {
            "key": "gym_mocked",
            "desc": "Progress gym bagian back yang Dina bagikan malah dijadikan candaan di grup.",
            "when": now - timedelta(days=25),
            "valence": -0.78,
            "significance": 0.86,
            "session": s2,
            "triggers": ["gym_mockery", "fear_baper"],
            "topics": ["bullying", "body", "belonging"],
            "people": ["raka"],
            "emotions": [("embarrassed", 0.84, -0.80, "Aku jadi tidak ingin post apa pun lagi."), ("afraid", 0.80, -0.76, "Kalau aku negur, mereka bisa pergi.")],
            "thoughts": ["too_sensitive", "lose_circle"],
            "behaviors": ["skip_studio", "mute_group"],
        },
        {
            "key": "naya_support",
            "desc": "Dina bercerita ke Naya dan mendapat validasi bahwa bercanda tetap bisa melukai.",
            "when": now - timedelta(days=13),
            "valence": 0.35,
            "significance": 0.72,
            "session": s3,
            "triggers": ["group_chat"],
            "topics": ["belonging", "boundary"],
            "people": ["naya"],
            "emotions": [("relieved", 0.56, 0.42, "Akhirnya ada yang ngerti aku tidak lebay."), ("anxious", 0.48, -0.30, "Aku tetap takut kalau grup tahu.")],
            "thoughts": ["small_boundary"],
            "behaviors": ["talk_naya"],
        },
        {
            "key": "soft_boundary_sent",
            "desc": "Dina mengirim pesan personal ke Raka dan meminta agar video pribadinya tidak dijadikan bahan filter lagi.",
            "when": now - timedelta(days=4),
            "valence": 0.25,
            "significance": 0.78,
            "session": s4,
            "triggers": ["fear_baper"],
            "topics": ["boundary", "shame", "bullying"],
            "people": ["raka", "naya"],
            "emotions": [("nervous", 0.60, -0.35, "Tangan gemetar saat kirim pesan."), ("proud", 0.58, 0.50, "Aku tetap kirim karena aku butuh jaga diri.")],
            "thoughts": ["small_boundary", "effort_valid"],
            "behaviors": ["soft_boundary", "talk_naya"],
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
                await link_thought_emotion_association(thoughts[tkey], eid, row["session"], strength=0.82)
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=10,
        severity_label="moderate",
        item_responses={"q1": 2, "q2": 2, "q3": 1, "q4": 1, "q5": 1, "q6": 2, "q7": 1, "q8": 0, "q9": 0},
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=35, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    phq9_s2 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s2,
        instrument="PHQ-9",
        score=13,
        severity_label="moderate",
        item_responses={"q1": 2, "q2": 2, "q3": 2, "q4": 2, "q5": 1, "q6": 2, "q7": 1, "q8": 1, "q9": 0},
        delta_from_previous=3,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=24, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s2 id: {phq9_s2}")

    phq9_s4 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s4,
        instrument="PHQ-9",
        score=9,
        severity_label="mild",
        item_responses={"q1": 1, "q2": 1, "q3": 1, "q4": 1, "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 1},
        delta_from_previous=-4,
        q9_score=1,
        administered_at=_iso(now - timedelta(days=3, hours=1, minutes=20)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s4 id: {phq9_s4}")

    for tkey, conf in [("bullying", 0.94), ("shame", 0.88), ("boundary", 0.82), ("belonging", 0.78)]:
        await link_user_recurring_theme(cfg.user_id, topic_ids[tkey], s4, confidence=conf)

    for sess_id, summary, imp in [
        (s1, "Dina merasa dipermalukan setelah cover lagunya dijadikan bahan filter. PHQ-9 = 10.", 0.82),
        (s2, "Bullying berpindah ke progress gym. Dina takut dianggap baperan dan mulai menarik diri. PHQ-9 = 13.", 0.88),
        (s3, "Naya menjadi protective factor. Dina mulai percaya batas bisa dimulai dari satu orang aman.", 0.78),
        (s4, "Dina mengirim soft boundary ke Raka. PHQ-9 turun ke 9 meski q9 = 1 perlu safety check ringan.", 0.86),
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

    print("Seed scenario 5 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (2 SUPERSEDES arcs)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print("  assessments: 3 (PHQ-9 arc 10->13->9)")


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
        description="Seed KG Scenario 5 - Dina (peer bullying and boundary recovery)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
