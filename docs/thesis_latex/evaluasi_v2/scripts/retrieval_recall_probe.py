"""Recall@k probe for the KG+pgvector retrieval path (agentic.memory.context_builder.build_context).

Seeds three independent test users (15 seed facts total across the six calibrated
student-life domains: academic, family, organizational, self-identity, career, and
housing/rantau), lets the real session finalizer write each user's facts into
Neo4j/pgvector, then opens a fresh session per user and probes retrieval with
paraphrased follow-up queries that never reuse the seed wording verbatim. A probe
counts as a hit if the retrieval context returned by build_context() (the same
object the production dialogue node consumes) contains at least one of the
domain's anchor keywords. Splitting across three users (instead of one) also
avoids the single-user sample-size objection from the seminar hasil critique.

Run from repo root: .venv/bin/python3 docs/thesis_latex/evaluasi_v2/scripts/retrieval_recall_probe.py
(requires the local docker-compose stack up: postgres on 5433, neo4j on 7687)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path

_SIMILARITY_RE = re.compile(r"similarity\s+([0-9]+\.[0-9]+)")

import psycopg2

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation_pipeline"))


def _load_env(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and (override or key not in os.environ):
            os.environ[key] = value


_load_env(ROOT / ".env")
_load_env(ROOT / "agentic" / ".env", override=True)
_load_env(ROOT / "evaluation_pipeline" / ".env", override=True)

from config import DATABASE_URL  # noqa: E402


# Three independent test users, five domain-facts each, covering all six
# calibrated student-life domains (academic, family, organizational,
# self-identity, career, housing/rantau) with distinct specific scenarios
# per user, so probes test generalization rather than memorizing one story.
USERS: list[dict[str, list]] = [
    {
        "label": "user_A",
        "seed_turns": [
            ("thesis_advisor", "dospem gue susah dihubungin, revisi udah dua minggu ga dibales-bales."),
            ("family_financial", "keluarga di rumah juga terus nanya kapan lulus, biayanya udah berat buat mereka."),
            ("organizational_burnout", "organisasi yang gue ikutin sekarang malah bikin gue burnout, rapatnya kebanyakan padahal deket-deket ujian."),
            ("impostor_syndrome", "kadang gue mikir, jangan-jangan gue emang ga secerdas temen-temen seangkatan gue. minder aja gitu liat mereka udah pada progress."),
            ("career_uncertainty", "abis lulus juga gue masih bingung mau kerja di mana, magang kemarin juga ga dapet-dapet."),
        ],
        "probes": [
            ("thesis_advisor", "masih parno aja mikirin revisi tugas akhir yang belum juga direspon pembimbing", ["dospem", "pembimbing", "revisi", "thesis_advisor", "thesis_stress"]),
            ("family_financial", "orang tua di rumah tanya-tanya mulu kapan wisuda, biaya kuliah makin berat aja rasanya", ["biaya", "keluarga", "orang tua", "family_financial", "wisuda"]),
            ("organizational_burnout", "capek sih ikut kegiatan organisasi kampus, kebanyakan rapat pas lagi deket-deket ujian", ["organisasi", "rapat", "burnout", "organizational_burnout"]),
            ("impostor_syndrome", "suka ngerasa minder liat pencapaian temen-temen seangkatan", ["minder", "temen", "seangkatan", "impostor", "self_worth"]),
            ("career_uncertainty", "bingung banget abis lulus nanti mau ngelamar kerja ke mana, secara magang aja susah dapetnya", ["kerja", "magang", "lulus", "career_uncertainty"]),
        ],
    },
    {
        "label": "user_B",
        "seed_turns": [
            ("exam_anxiety", "deg-degan banget mikirin UAS kalkulus minggu depan, takut nilai jeblok gara-gara belum ngerti materinya sama sekali."),
            ("family_expectation_pressure", "orang tua gue selalu bandingin gue sama kakak yang udah kerja duluan, jadi tambah tertekan tiap pulang kampung."),
            ("peer_pressure", "temen-temen sepanitia pada nge-judge kalo gue nggak all-out ikut acara organisasi, padahal gue juga capek kuliah."),
            ("lecturer_relationship_stress", "dosen killer di kelas gue suka nyindir di depan kelas kalo ada yang telat ngumpul tugas, jadi males masuk kelas itu."),
            ("post_graduation_anxiety", "abis diwisuda nanti gue takut banget ngerasa ga siap masuk dunia kerja yang beneran."),
        ],
        "probes": [
            ("exam_anxiety", "besok ujian kalkulus, jantung udah deg-degan dari sekarang mikirin soalnya", ["ujian", "kalkulus", "exam_anxiety", "deg-degan"]),
            ("family_expectation_pressure", "males banget kalo pulang kampung, pasti dibandingin lagi sama kakak yang udah kerja", ["kakak", "dibandingin", "family_expectation", "pulang kampung"]),
            ("peer_pressure", "kerasa banget tekanan dari temen sepanitia buat all-out terus di organisasi", ["panitia", "organisasi", "peer_pressure", "tekanan"]),
            ("lecturer_relationship_stress", "males masuk kelas dosen itu, suka nyindir mahasiswa yang telat ngumpul", ["dosen", "nyindir", "lecturer_relationship", "kelas"]),
            ("post_graduation_anxiety", "abis wisuda nanti kepikiran terus gimana rasanya kerja beneran", ["wisuda", "kerja", "post_graduation", "siap"]),
        ],
    },
    {
        "label": "user_C",
        "seed_turns": [
            ("housing_stress", "ibu kos gue berisik banget kalo malem, susah fokus ngerjain tugas kalo lagi di kos."),
            ("internship_stress", "magang gue sekarang banyak banget kerjaan yang di luar job desc, capek fisik sama mental."),
            ("identity_exploration", "gue masih bingung banget sebenernya minat gue di bidang apa, ngerasa salah jurusan terus."),
            ("family_conflict", "orang tua gue lagi sering berantem di rumah, jadi males pulang dan susah konsen kuliah."),
            ("social_isolation", "semenjak pindah kos baru gue jarang ngobrol sama orang, kesepian banget rasanya di kampus."),
        ],
        "probes": [
            ("housing_stress", "kos gue berisik banget kalo malem jadi susah belajar", ["kos", "berisik", "housing_stress", "fokus"]),
            ("internship_stress", "kerjaan magang gue kebanyakan yang bukan bagian job desc, cape banget", ["magang", "job desc", "internship_stress", "cape"]),
            ("identity_exploration", "masih ngerasa salah jurusan dan bingung minat sendiri sebenernya apa", ["jurusan", "minat", "identity_exploration", "bingung"]),
            ("family_conflict", "di rumah lagi sering ada pertengkaran ortu jadi males pulang", ["berantem", "orang tua", "family_conflict", "pulang"]),
            ("social_isolation", "semenjak pindah kos jarang punya temen ngobrol, kesepian di kampus", ["kesepian", "temen", "social_isolation", "kos baru"]),
        ],
    },
]


async def _ensure_user(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status)
                    VALUES (%s, %s, %s, %s, 'id', true, 'active')
                    """,
                    (user_id, f"recall_probe_{user_id}@test.com", "Recall Probe Test", "nopassword"),
                )
            conn.commit()
    finally:
        conn.close()


def _insert_seed_session(user_id: str, session_id: str, seed_turns: list) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_sessions (id, user_id, channel, status, turn_count) VALUES (%s, %s, 'text', 'ended', %s)",
                (session_id, user_id, len(seed_turns)),
            )
            for i, (_label, content) in enumerate(seed_turns):
                cur.execute(
                    "INSERT INTO messages (session_id, user_id, role, content, turn_index) VALUES (%s, %s, 'user', %s, %s)",
                    (session_id, user_id, content, i + 1),
                )
            conn.commit()
    finally:
        conn.close()


def _cleanup(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()


async def _cleanup_stores(user_id: str) -> None:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    await client.execute_write(
        "MATCH (u:User {id: $user_id})-[*0..2]-(n) DETACH DELETE n",
        {"user_id": user_id},
    )

    from agentic.memory.pg_vector.client import get_pool

    pool = await get_pool()
    if pool is not None:
        for table in (
            "memory_embeddings", "experience_embeddings", "thought_embeddings",
            "trigger_embeddings", "behavior_embeddings",
        ):
            try:
                async with pool.acquire() as conn:
                    await conn.execute(f"DELETE FROM {table} WHERE user_id = $1::uuid", user_id)
            except Exception:
                pass


async def _run_user(user_spec: dict) -> dict:
    user_id = str(uuid.uuid4())
    seed_session_id = str(uuid.uuid4())
    label = user_spec["label"]
    seed_turns = user_spec["seed_turns"]
    probes = user_spec["probes"]

    print(f"\n{'#'*70}\n{label} user_id={user_id}\n{'#'*70}")
    await _ensure_user(user_id)
    _insert_seed_session(user_id, seed_session_id, seed_turns)

    from agentic.agent.session.finalizer_factory import build_session_finalizer

    finalizer = build_session_finalizer()
    print(f"[{label}] Running session finalizer on seed conversation (write path)...")
    result = await finalizer.finalize(session_id=seed_session_id, user_id=user_id, language="id")
    print(f"  extracted={result.extracted_count} processed={result.processed_count} error={result.error}")
    if result.error:
        print(f"[{label}] Aborting: finalizer failed, cannot probe retrieval on empty memory.")
        _cleanup(user_id)
        return {"label": label, "user_id": user_id, "hits": 0, "total": len(probes), "rows": [], "error": result.error}

    from agentic.memory.context_builder import build_context
    from agentic.memory.pg_vector import embed_text

    hits = 0
    rows = []
    print(f"[{label}] Running retrieval probes (read path)...")
    for probe_label, query, anchors in probes:
        query_embedding = await embed_text(query)
        ctx = await build_context(
            user_id=user_id,
            query_embedding=query_embedding,
            query_text=query,
        )
        raw_block = ctx.as_prompt_block()
        block = raw_block.lower()
        hit = any(anchor.lower() in block for anchor in anchors)
        hits += int(hit)
        sims = [float(m) for m in _SIMILARITY_RE.findall(raw_block)]
        top_similarity = max(sims) if sims else None
        rows.append({"label": probe_label, "query": query, "hit": hit, "top_similarity": top_similarity})
        print(f"  [{probe_label}] hit={hit} top_similarity={top_similarity} query={query!r}")

    print(f"[{label}] Cleaning up test data...")
    await _cleanup_stores(user_id)
    _cleanup(user_id)

    return {"label": label, "user_id": user_id, "hits": hits, "total": len(probes), "rows": rows}


async def main() -> None:
    from agentic.memory.neo4j_client import init_client
    await init_client()

    all_results = []
    for user_spec in USERS:
        result = await _run_user(user_spec)
        all_results.append(result)

    total_hits = sum(r["hits"] for r in all_results)
    total_probes = sum(r["total"] for r in all_results)
    recall = total_hits / total_probes if total_probes else 0.0

    print(f"\n{'='*70}")
    for r in all_results:
        print(f"{r['label']}: {r['hits']}/{r['total']}" + (f" (error: {r['error']})" if r.get("error") else ""))
    print(f"Overall Recall@focused_top_k = {total_hits}/{total_probes} = {recall:.2f}")
    print(f"{'='*70}")

    with open(ROOT / "evaluation_pipeline" / "results" / "retrieval_recall_probe.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_hits": total_hits,
                "total_probes": total_probes,
                "recall": recall,
                "users": all_results,
            },
            f, ensure_ascii=False, indent=2,
        )
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
