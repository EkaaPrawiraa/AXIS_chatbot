"""utility/kg_seeder_scenario/scenario_3/seed.py

Seed Scenario 3 — Maya: Psychology student with mixed emotional arc.

Maya is a 2nd-year Psychology student who starts with mild depression
(PHQ-9 = 9), worsens under relationship stress (PHQ-9 = 12, moderate),
and gradually recovers through CBT and social support (PHQ-9 = 7, mild).

Her arc demonstrates:
  - PHQ-9 worsening and recovery with delta tracking
  - Multiple SUPERSEDES arcs (two separate CBT reframe chains)
  - A complicated relationship (Rafi) producing both positive and negative
    experiences across different sessions — the same Person node appears
    in very different emotional contexts
  - Thought-Thought SUPERSEDES tracked bi-temporally per session
  - All 18 relationship types exercised with dense cross-node wiring

Usage:
  python -m utility.kg_seeder_scenario.scenario_3.seed --run
  python -m utility.kg_seeder_scenario.scenario_3.seed --purge
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

_DEFAULT_USER_ID = "05154a8d-e38e-5738-9f00-507e648f3a87"
_DEFAULT_NS      = "seed-scenario-3"
_SCENARIO_NAME   = "scenario3_maya"
_PASSWORD_HASH   = "$2a$12$ejA5OBnZlrZ8bC6At2lD5uuyCZFm7QkQjSk8mGa9jSQqwy38yke/y"


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
    # s1: ~8 weeks ago — first session, mild depression baseline
    # s2: ~6 weeks ago — relationship tension starts escalating
    # s3: ~4 weeks ago — relationship crisis, PHQ-9 peaks at 12 (moderate)
    # s4: ~2 weeks ago — CBT reframe session, self-compassion work
    # s5: ~4 days ago  — recovery confirmed, PHQ-9 = 7 (mild, improving)
    sids = _session_ids_for_namespace(cfg.namespace, count=5)
    s1, s2, s3, s4, s5 = sids["s1"], sids["s2"], sids["s3"], sids["s4"], sids["s5"]

    session_rows = [
        {
            "id": s1,
            "started_at": now - timedelta(days=56, hours=2),
            "ended_at":   now - timedelta(days=56, hours=1),
            "summary": (
                "Maya bercerita tentang beratnya perkuliahan Psikologi dan rasa kurang "
                "percaya diri. Ada perasaan sedih yang menetap tapi sulit diidentifikasi "
                "penyebabnya. PHQ-9 dilakukan: skor 9 (mild)."
            ),
        },
        {
            "id": s2,
            "started_at": now - timedelta(days=42, hours=3),
            "ended_at":   now - timedelta(days=42, hours=2),
            "summary": (
                "Maya mulai bercerita tentang Rafi — hubungan yang sering panas dingin. "
                "Merasa kelelahan emosional setelah pertengkaran berulang. "
                "Mulai muncul pola pikir 'aku yang selalu salah'."
            ),
        },
        {
            "id": s3,
            "started_at": now - timedelta(days=28, hours=2),
            "ended_at":   now - timedelta(days=28, hours=1),
            "summary": (
                "Rafi mengancam mengakhiri hubungan. Maya merasa hancur dan tidak berdaya. "
                "PHQ-9 naik ke 12 (moderate, delta +3). Ada pikiran menyalahkan diri sendiri "
                "yang kuat. Protokol safety diperiksa — tidak ada ideasi."
            ),
        },
        {
            "id": s4,
            "started_at": now - timedelta(days=14, hours=2),
            "ended_at":   now - timedelta(days=14, hours=1),
            "summary": (
                "CBT thought challenging dilakukan untuk pikiran 'aku selalu salah' dan "
                "'aku tidak layak dicintai'. Lena memberikan perspektif yang membantu. "
                "Maya mulai menerima bahwa dinamika hubungan adalah tanggung jawab bersama."
            ),
        },
        {
            "id": s5,
            "started_at": now - timedelta(days=4, hours=1),
            "ended_at":   now - timedelta(days=4),
            "summary": (
                "Maya memutuskan batasan yang lebih sehat dengan Rafi. "
                "Merasa lebih ringan. PHQ-9 turun ke 7 (mild, delta -5). "
                "Fokus mulai berpindah ke pengembangan diri dan karir."
            ),
        },
    ]

    await get_client().execute_write(
        """
        MERGE (u:User {id: $user_id})
        ON CREATE SET
            u.name               = 'Maya Putri',
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
        "relationship":   ("relationship-stress",     "social"),
        "self_worth":     ("self-worth",              "identity"),
        "academic":       ("academic-pressure",       "academic"),
        "emotional_reg":  ("emotional-regulation",    "mental_health"),
        "self_blame":     ("self-blame-pattern",      "mental_health"),
        "future":         ("future-uncertainty",      "identity"),
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
    # Rafi's sentiment progresses: -0.2 (neutral-negative) → updated inline per session
    # But since write_subject is MERGE-based by name, we write once and use same id throughout.
    people: dict[str, str] = {}
    person_specs = [
        ("rafi",  "Rafi",       "partner",  -0.35,  "complicated"),
        ("lena",  "Lena",       "friend",    0.80,   "supportive"),
        ("mama",  "Mama",       "parent",    0.40,   "complicated"),
        ("dosen", "Bu Ratna",   "professor", 0.50,   "neutral"),
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
        "conflict_rafi":  ("social",    "pertengkaran dan ancaman putus dari Rafi"),
        "academic_load":  ("academic",  "tugas kuliah yang menumpuk bersamaan"),
        "rejection_fear": ("social",    "ketakutan ditolak dan ditinggalkan orang"),
        "comparison":     ("social",    "membandingkan diri dengan teman yang tampak lebih bahagia"),
        "loneliness":     ("social",    "rasa kesepian di tengah keramaian"),
    }
    triggers: dict[str, str] = {}
    for key, (cat, desc) in trigger_specs.items():
        embedding = await embed_text(desc)
        first_sess = s2 if "rafi" in key or "rejection" in key else s1
        tid = await write_trigger(
            TriggerInput(
                category=cat,
                description=desc,
                user_id=cfg.user_id,
                session_id=first_sess,
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
            importance=0.65,
        )

    # Behaviors
    behavior_specs = {
        "cry_alone":       ("avoidance",        "menangis sendirian di kamar tanpa mencari bantuan",  False),
        "overthinking":    ("rumination",        "mengulang percakapan dengan Rafi berjam-jam",         False),
        "isolation":       ("social_withdrawal", "menolak ajakan Lena karena merasa tidak layak",       False),
        "journaling":      ("help_seeking",      "menulis jurnal emosi sebagai bentuk self-expression",  True),
        "reach_out_lena":  ("help_seeking",      "menghubungi Lena untuk berbagi cerita",                True),
        "self_compassion": ("help_seeking",      "latihan self-compassion dari panduan CBT",              True),
        "boundary_set":    ("help_seeking",      "menetapkan batasan komunikasi yang sehat dengan Rafi",  True),
        "study_group":     ("help_seeking",      "bergabung kembali ke study group setelah menarik diri", True),
    }
    behaviors: dict[str, str] = {}
    for key, (cat, desc, adaptive) in behavior_specs.items():
        bid = await write_behavior(
            BehaviorInput(
                description=desc,
                category=cat,
                adaptive=adaptive,
                user_id=cfg.user_id,
                session_id=s2,
            )
        )
        behaviors[key] = bid
        await _tag_node(node_id=bid, namespace=cfg.namespace)

    # Thoughts
    # Two SUPERSEDES arcs:
    #   Arc A: "aku selalu yang salah" → "tanggung jawab adalah milik berdua"
    #   Arc B: "aku tidak layak dicintai" → "aku layak mendapat hubungan yang sehat"
    thought_specs = {
        # Arc A — self-blame
        "always_my_fault":   ("Aku selalu yang salah dalam setiap pertengkaran kami",
                               "automatic", "personalization",    0.85),
        "shared_responsiblty": ("Konflik dalam hubungan adalah tanggung jawab berdua, bukan hanya aku",
                                "automatic", None,                 0.75),
        # Arc B — worthiness
        "unworthy_love":     ("Aku tidak layak untuk dicintai dengan sungguh-sungguh",
                               "core_belief", "labeling",          0.80),
        "worthy_healthy":    ("Aku layak mendapatkan hubungan yang sehat dan saling menghormati",
                               "core_belief", None,                 0.78),
        # Supporting thoughts
        "hopeless_future":   ("Tidak ada yang akan berubah, hidupku akan selalu seperti ini",
                               "automatic", "overgeneralization",  0.70),
        "catastrophize":     ("Kalau Rafi pergi, aku tidak akan bisa baik-baik saja",
                               "automatic", "catastrophizing",     0.75),
        "academic_fail":     ("Aku tidak bisa fokus kuliah dan akan gagal semester ini",
                               "automatic", "fortune_telling",     0.65),
        "self_compassion_t": ("Aku sedang berjuang dan itu wajar; aku patut memperlakukan diriku dengan baik",
                               "intermediate", None,               0.80),
    }
    thoughts: dict[str, str] = {}
    for key, (content, ttype, dist, bel) in thought_specs.items():
        # Reframed thoughts appear in later sessions
        if key in ("shared_responsiblty", "worthy_healthy", "self_compassion_t"):
            sess = s4
        elif key in ("always_my_fault", "unworthy_love", "catastrophize"):
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

    # SUPERSEDES arcs (CBT reframe)
    # Arc A: self-blame → shared responsibility
    await _write_supersession(
        old_thought_id=thoughts["always_my_fault"],
        new_thought_id=thoughts["shared_responsiblty"],
        reason="CBT evidence review: listed specific instances where Rafi also contributed to conflict",
        session_id=s4,
        at=_iso(now - timedelta(days=14, hours=1, minutes=40)),
    )
    # Arc B: unworthiness → worthiness core belief reframe
    await _write_supersession(
        old_thought_id=thoughts["unworthy_love"],
        new_thought_id=thoughts["worthy_healthy"],
        reason="CBT values clarification: user articulated what a healthy relationship looks like and recognized she deserves it",
        session_id=s4,
        at=_iso(now - timedelta(days=14, hours=1, minutes=10)),
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
        # s1: Baseline mild depression
        {
            "key":          "academic_overwhelm",
            "desc":         "Menghadapi tiga deadline tugas kuliah sekaligus dan tidak tahu harus mulai dari mana.",
            "when":         now - timedelta(days=60),
            "valence":      -0.60,
            "significance": 0.75,
            "session":      s1,
            "triggers":     ["academic_load"],
            "topics":       ["academic", "self_worth"],
            "people":       ["dosen"],
            "emotions":     [
                ("overwhelmed", 0.75, -0.70, "Semua menumpuk dan aku tidak tahu harus mulai dari mana."),
                ("anxious",     0.70, -0.65, "Takut tidak bisa selesaikan semuanya."),
            ],
            "thoughts":  ["hopeless_future", "academic_fail"],
            "behaviors": ["overthinking", "cry_alone"],
        },
        {
            "key":          "lena_hangout_s1",
            "desc":         "Nongkrong dengan Lena setelah kuliah; sempat tertawa meski hati masih berat.",
            "when":         now - timedelta(days=58),
            "valence":      0.35,
            "significance": 0.55,
            "session":      s1,
            "triggers":     ["loneliness"],
            "topics":       ["self_worth", "emotional_reg"],
            "people":       ["lena"],
            "emotions":     [
                ("relieved", 0.50, 0.40, "Sebentar bisa lupa dari masalah."),
                ("sad",      0.45, -0.40, "Tapi rasa sedih tetap ada di balik senyum."),
            ],
            "thoughts":  ["hopeless_future"],
            "behaviors": ["reach_out_lena"],
        },
        # s2: Relationship stress escalates
        {
            "key":          "rafi_argument_1",
            "desc":         "Rafi marah karena Maya terlambat membalas pesan; berakhir dengan pertengkaran lewat telepon.",
            "when":         now - timedelta(days=45),
            "valence":      -0.70,
            "significance": 0.80,
            "session":      s2,
            "triggers":     ["conflict_rafi", "rejection_fear"],
            "topics":       ["relationship", "self_blame"],
            "people":       ["rafi"],
            "emotions":     [
                ("guilty",   0.75, -0.65, "Aku pasti yang salah lagi."),
                ("anxious",  0.70, -0.70, "Takut dia akan meninggalkanku."),
                ("angry",    0.40, -0.30, "Tapi ada juga marah yang aku pendam."),
            ],
            "thoughts":  ["always_my_fault", "unworthy_love"],
            "behaviors": ["cry_alone", "overthinking"],
        },
        {
            "key":          "comparison_classmates",
            "desc":         "Melihat foto teman-teman di media sosial tampak bahagia dan berprestasi.",
            "when":         now - timedelta(days=43),
            "valence":      -0.60,
            "significance": 0.65,
            "session":      s2,
            "triggers":     ["comparison", "loneliness"],
            "topics":       ["self_worth", "self_blame"],
            "people":       [],
            "emotions":     [
                ("sad",       0.65, -0.60, "Kenapa hidupku tidak seperti mereka?"),
                ("envious",   0.55, -0.55, "Aku iri dengan kebahagiaan orang lain."),
            ],
            "thoughts":  ["hopeless_future", "always_my_fault"],
            "behaviors": ["isolation", "overthinking"],
        },
        # s3: Crisis point
        {
            "key":          "rafi_threat_breakup",
            "desc":         "Rafi bilang 'mungkin kita harus istirahat dulu' setelah pertengkaran soal kepercayaan.",
            "when":         now - timedelta(days=30),
            "valence":      -0.90,
            "significance": 0.95,
            "session":      s3,
            "triggers":     ["conflict_rafi", "rejection_fear"],
            "topics":       ["relationship", "self_worth", "self_blame"],
            "people":       ["rafi"],
            "emotions":     [
                ("devastated",   0.90, -0.90, "Aku hancur mendengar kata-kata itu."),
                ("hopeless",     0.85, -0.85, "Rasanya tidak ada yang bisa diperbaiki."),
                ("ashamed",      0.70, -0.70, "Aku malu pada diri sendiri."),
            ],
            "thoughts":  ["always_my_fault", "unworthy_love", "catastrophize"],
            "behaviors": ["cry_alone", "isolation"],
        },
        {
            "key":          "mama_call_s3",
            "desc":         "Menelepon Mama sambil menangis; Mama mencoba menghibur meski tidak mengerti sepenuhnya.",
            "when":         now - timedelta(days=29),
            "valence":      -0.30,
            "significance": 0.65,
            "session":      s3,
            "triggers":     ["rejection_fear"],
            "topics":       ["relationship", "emotional_reg"],
            "people":       ["mama"],
            "emotions":     [
                ("sad",      0.80, -0.75, "Aku tidak bisa berhenti menangis."),
                ("grateful", 0.40, 0.30, "Setidaknya ada Mama yang mau mendengar."),
            ],
            "thoughts":  ["hopeless_future", "catastrophize"],
            "behaviors": ["reach_out_lena", "cry_alone"],
        },
        # s4: CBT reframe session
        {
            "key":          "cbt_thought_challenge",
            "desc":         "Dalam sesi, Maya menelusuri bukti-bukti yang bertentangan dengan pikiran 'aku selalu salah'.",
            "when":         now - timedelta(days=15),
            "valence":      0.30,
            "significance": 0.90,
            "session":      s4,
            "triggers":     ["self_blame"],        # using topic key as trigger key won't work; use existing trigger
            "topics":       ["self_blame", "emotional_reg", "self_worth"],
            "people":       [],
            "emotions":     [
                ("hopeful",    0.60, 0.55, "Mungkin selama ini aku terlalu keras pada diri sendiri."),
                ("surprised",  0.55, 0.45, "Ternyata ada banyak saat di mana aku tidak salah."),
            ],
            "thoughts":  ["shared_responsiblty", "self_compassion_t"],
            "behaviors": ["journaling", "self_compassion"],
        },
        {
            "key":          "lena_support_s4",
            "desc":         "Lena memberikan perspektif dari luar: 'Menurutku, Rafi yang sering bikin kamu nangis, bukan sebaliknya.'",
            "when":         now - timedelta(days=14, hours=4),
            "valence":      0.55,
            "significance": 0.80,
            "session":      s4,
            "triggers":     ["loneliness"],
            "topics":       ["relationship", "self_worth"],
            "people":       ["lena"],
            "emotions":     [
                ("touched",    0.75, 0.65, "Lena peduli padaku dan melihat apa yang aku tidak mau lihat."),
                ("grateful",   0.70, 0.65, "Beruntung punya teman seperti Lena."),
                ("conflicted", 0.50, -0.20, "Tapi aku masih belum bisa sepenuhnya percaya diri."),
            ],
            "thoughts":  ["worthy_healthy", "shared_responsiblty"],
            "behaviors": ["reach_out_lena", "journaling"],
        },
        # s5: Recovery
        {
            "key":          "boundary_setting",
            "desc":         "Maya menetapkan batasan dengan Rafi — tidak akan merespons pesan di atas jam 10 malam.",
            "when":         now - timedelta(days=6),
            "valence":      0.65,
            "significance": 0.85,
            "session":      s5,
            "triggers":     ["conflict_rafi"],    # same trigger, healthy response now
            "topics":       ["relationship", "self_worth", "emotional_reg"],
            "people":       ["rafi", "lena"],
            "emotions":     [
                ("proud",      0.70, 0.65, "Aku akhirnya bisa menetapkan batasan."),
                ("anxious",    0.35, -0.25, "Sedikit takut Rafi akan marah."),
                ("relieved",   0.65, 0.60, "Tapi rasanya juga lega."),
            ],
            "thoughts":  ["worthy_healthy", "self_compassion_t"],
            "behaviors": ["boundary_set", "journaling"],
        },
        {
            "key":          "study_group_return",
            "desc":         "Bergabung kembali ke study group Psikologi setelah dua minggu menarik diri.",
            "when":         now - timedelta(days=4, hours=3),
            "valence":      0.70,
            "significance": 0.70,
            "session":      s5,
            "triggers":     ["academic_load", "loneliness"],
            "topics":       ["academic", "self_worth", "future"],
            "people":       ["lena", "dosen"],
            "emotions":     [
                ("hopeful",   0.65, 0.60, "Rasanya menyenangkan bisa kembali bersama teman-teman."),
                ("motivated", 0.60, 0.55, "Aku ingin fokus pada hal-hal yang membuatku berkembang."),
            ],
            "thoughts":  ["self_compassion_t", "worthy_healthy"],
            "behaviors": ["study_group", "reach_out_lena"],
        },
    ]

    exp_ids: dict[str, str] = {}
    # Map "self_blame" topic string to the correct key in triggers dict
    # (note: "self_blame" is a topic key but was incorrectly used as trigger key above — use "academic_load" instead)
    trigger_key_map = {"self_blame": "academic_load"}

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

        # Triggers → Experience
        for tkey in row["triggers"]:
            resolved = trigger_key_map.get(tkey, tkey)
            if resolved in triggers:
                await link_experience_to_trigger(exp_id, triggers[resolved], row["session"])

        # Experience → Topic
        for tkey in row["topics"]:
            if tkey in topic_ids:
                await link_to_topic(exp_id, "Experience", topic_ids[tkey], row["session"])

        # Experience → Person
        for pkey in row["people"]:
            await link_experience_to_person(exp_id, people[pkey], row["session"])

        # Build emotion nodes + downstream chain
        emotion_ids: list[str] = []
        for (lab, inten, val, txt) in row["emotions"]:
            eid = await mk_emotion(lab, float(inten), float(val), txt, row["session"])
            emotion_ids.append(eid)
            await link_experience_to_emotion(exp_id, eid, row["session"])
            # Emotion → Topic
            for tkey in row["topics"][:2]:
                if tkey in topic_ids:
                    await link_to_topic(eid, "Emotion", topic_ids[tkey], row["session"])

        # Thought cross-links across all emotions in this experience
        for tkey in row["thoughts"]:
            for eid in emotion_ids:
                await link_emotion_to_thought(eid, thoughts[tkey], row["session"])
                await link_thought_emotion_association(
                    thoughts[tkey], eid, row["session"], strength=0.85,
                )

        # Behavior: from both emotion and thought sources
        for bkey in row["behaviors"]:
            if emotion_ids:
                await link_to_behavior(emotion_ids[0], "Emotion", behaviors[bkey], row["session"])
            for tkey in row["thoughts"]:
                await link_to_behavior(thoughts[tkey], "Thought", behaviors[bkey], row["session"])

    # PHQ-9 Assessment nodes
    # s1: score=9, mild (baseline)
    phq9_s1 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s1,
        instrument="PHQ-9",
        score=9,
        severity_label="mild",
        item_responses={
            "q1": 1, "q2": 2, "q3": 1, "q4": 1,
            "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 0,
        },
        delta_from_previous=None,
        q9_score=0,
        administered_at=_iso(now - timedelta(days=56, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s1 id: {phq9_s1}")

    # s3: score=12, moderate (worsening, delta=+3)
    phq9_s3 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s3,
        instrument="PHQ-9",
        score=12,
        severity_label="moderate",
        item_responses={
            "q1": 2, "q2": 2, "q3": 2, "q4": 1,
            "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 1,
        },
        delta_from_previous=3,    # +3 from s1 — crosses worsening threshold
        q9_score=1,
        administered_at=_iso(now - timedelta(days=28, hours=1, minutes=30)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s3 id (moderate): {phq9_s3}")

    # s5: score=7, mild (recovering, delta=-5)
    phq9_s5 = await _write_assessment_node(
        user_id=cfg.user_id,
        session_id=s5,
        instrument="PHQ-9",
        score=7,
        severity_label="mild",
        item_responses={
            "q1": 1, "q2": 1, "q3": 1, "q4": 1,
            "q5": 1, "q6": 0, "q7": 1, "q8": 1, "q9": 0,
        },
        delta_from_previous=-5,   # -5 from s3 — clear improvement
        q9_score=0,
        administered_at=_iso(now - timedelta(days=4, hours=0, minutes=45)),
        namespace=cfg.namespace,
    )
    print(f"  Assessment s5 id (recovering): {phq9_s5}")

    # User recurring themes
    for tkey, conf in [
        ("relationship",  0.92),
        ("self_worth",    0.90),
        ("self_blame",    0.80),
        ("emotional_reg", 0.75),
    ]:
        await link_user_recurring_theme(
            cfg.user_id, topic_ids[tkey], s5, confidence=conf,
        )

    # Session memories
    memory_rows = [
        (s1, "Baseline: Maya merasakan sedih menetap dan kewalahan akademik. PHQ-9 = 9 (mild).", 0.70),
        (s2, "Konflik berulang dengan Rafi mulai menguras energi emosional. Pola pikir self-blame muncul.", 0.75),
        (s3, "Krisis: ancaman putus dari Rafi. PHQ-9 naik ke 12 (moderate, +3). Safety check dilakukan.", 0.90),
        (s4, "CBT thought challenging berhasil. Dua pikiran inti berhasil di-reframe dengan bantuan Lena.", 0.85),
        (s5, "Pemulihan: PHQ-9 turun ke 7 (-5 delta). Maya menetapkan batasan sehat dan kembali aktif secara sosial.", 0.80),
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

    print("Seed scenario 3 complete.")
    print(f"  user_id    : {cfg.user_id}")
    print(f"  namespace  : {cfg.namespace}")
    print(f"  sessions   : {len(session_rows)}")
    print(f"  topics     : {len(topic_ids)}")
    print(f"  people     : {len(people)}")
    print(f"  triggers   : {len(triggers)}")
    print(f"  thoughts   : {len(thoughts)} (2 SUPERSEDES arcs)")
    print(f"  behaviors  : {len(behaviors)}")
    print(f"  experiences: {len(exp_ids)}")
    print(f"  assessments: 3 (PHQ-9 arc 9→12→7)")


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
        description="Seed KG Scenario 3 — Maya (mixed emotional arc)",
        default_user_id=_DEFAULT_USER_ID,
        default_namespace=_DEFAULT_NS,
    )
    args = ap.parse_args()
    if args.run and args.purge:
        raise SystemExit("Pick one: --run or --purge")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
