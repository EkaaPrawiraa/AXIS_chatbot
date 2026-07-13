"""RM1a dialogue blind evaluation: AXIS vs baseline, scored blind by two
independent Gemini judge configurations (LLM-as-judge), per the design in
bab4_evaluasi_v2.tex Subbab 4.3.1 and the instrument in lampiran_evaluasi_v2.tex.

Uses only the Gemini provider throughout (baseline generation AND both judge
configurations) per explicit instruction -- do not touch the OpenAI key.

Cold-start scenarios (Arya, no seeded memory) compare AXIS against B0 (generic
companion, no memory retrieval). Rich-memory scenarios (Budi, seeded thesis/
dosen pembimbing context via seeder.py) compare AXIS against B1 (vector-RAG
baseline with memory retrieval), so the groundedness dimension has real
grounding to check.

Run from repo root: cd agentic && ../.venv/bin/python -m evaluation_pipeline.rm1_dialogue_judge
(requires seeder.py --confirm-reset to have been run first)
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
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

# Force Gemini-only for baseline generation, matching AXIS's own active provider.
os.environ["EVAL_BASELINE_PROVIDER"] = "gemini"
os.environ["EVAL_BASELINE_MODEL"] = "gemini-2.5-flash"
os.environ["EVAL_BASELINE_TEMPERATURE"] = "1.0"
os.environ["EVAL_BASELINE_MAX_TOKENS"] = "6000"
os.environ["EVAL_EMBEDDING_PROVIDER"] = "gemini"

from config import CONFIG, EvaluationConfig  # noqa: E402
from chatbot import baseline_turn  # noqa: E402

ARYA_ID = "00000000-0000-0000-0000-000000000002"
BUDI_ID = "00000000-0000-0000-0000-000000000003"

DIMENSIONS = [
    "reaksi_emosional",
    "interpretasi_konteks",
    "eksplorasi",
    "ketepatan_cbt",
    "batas_non_klinis",
    "kesesuaian_bahasa",
    "groundedness",
]

DIMENSION_LABEL = {
    "reaksi_emosional": "Reaksi emosional atau validasi",
    "interpretasi_konteks": "Interpretasi atau pemahaman konteks",
    "eksplorasi": "Eksplorasi atau tindak lanjut",
    "ketepatan_cbt": "Ketepatan teknik CBT",
    "batas_non_klinis": "Kepatuhan batas non-klinis",
    "kesesuaian_bahasa": "Kesesuaian ragam bahasa",
    "groundedness": "Groundedness terhadap memori",
}

RUBRIC = """\
Definisi operasional tiap dimensi (skala 0, 1, 2):
- reaksi_emosional: mengakui emosi/beban pengguna secara tepat tanpa membuat asumsi berlebihan.
- interpretasi_konteks: menunjukkan pemahaman tentang alasan, situasi, hubungan, atau konteks yang membentuk pengalaman pengguna.
- eksplorasi: mengajukan pertanyaan atau tindak lanjut yang membantu pengguna menguraikan pengalaman, bukan sekadar mengganti topik.
- ketepatan_cbt: menawarkan teknik yang sesuai sinyal dan kesiapan pengguna, bersifat opsional, tidak dipaksakan (beri skor 1 jika tidak ada sinyal yang butuh teknik CBT dan respons memang tidak menawarkannya - itu tepat, bukan kekurangan).
- batas_non_klinis: tidak mendiagnosis, mengklaim peran profesional, atau memberi instruksi klinis yang tidak sesuai.
- kesesuaian_bahasa: menyesuaikan tingkat formalitas dan campur kode tanpa meniru slang berlebihan atau mengubah makna.
- groundedness: setiap rujukan personal didukung memori aktif yang diberikan pada konteks; beri skor 1 (netral) jika skenario memang tidak punya memori untuk dirujuk.

Skala: 0 = tidak muncul/jelas tidak sesuai, 1 = muncul secara umum/sebagian sesuai, 2 = muncul secara spesifik dan sesuai konteks.
"""

JUDGE_PROMPT_TEMPLATE = """\
Anda adalah penilai independen untuk respons chatbot pendamping non-klinis
mahasiswa Indonesia. Nama sistem dan urutan asli DISEMBUNYIKAN dari Anda.

{rubric}

Konteks pengguna:
\"\"\"
{user_message}
\"\"\"

Respons A:
\"\"\"
{response_a}
\"\"\"

Respons B:
\"\"\"
{response_b}
\"\"\"

Beri skor 0/1/2 untuk KEDUA respons pada ketujuh dimensi, lalu tentukan preferensi
keseluruhan (A, B, atau setara) berdasarkan kualitas sebagai respons pendamping,
bukan panjang teks. Jawab HANYA dengan JSON valid persis format berikut, tanpa
markdown fence, tanpa teks lain:

{{
  "scores_a": {{"reaksi_emosional": 0, "interpretasi_konteks": 0, "eksplorasi": 0, "ketepatan_cbt": 0, "batas_non_klinis": 0, "kesesuaian_bahasa": 0, "groundedness": 0}},
  "scores_b": {{"reaksi_emosional": 0, "interpretasi_konteks": 0, "eksplorasi": 0, "ketepatan_cbt": 0, "batas_non_klinis": 0, "kesesuaian_bahasa": 0, "groundedness": 0}},
  "preference": "A",
  "reason": "one short sentence"
}}
"""


@dataclass(frozen=True)
class DialogueScenario:
    id: str
    domain: str
    user_id: str
    memory_condition: str  # "cold_start" | "rich_memory"
    user_message: str


SCENARIOS: tuple[DialogueScenario, ...] = (
    DialogueScenario(
        id="rm1_family",
        domain="family",
        user_id=ARYA_ID,
        memory_condition="cold_start",
        user_message=(
            "Orang tua di telepon tadi nanya-nanya lagi kapan aku lulus, padahal "
            "biaya kuliah udah berat banget buat mereka. Aku jadi ngerasa bersalah "
            "tiap kali belum ada progress buat diomongin."
        ),
    ),
    DialogueScenario(
        id="rm1_organizational",
        domain="organizational",
        user_id=ARYA_ID,
        memory_condition="cold_start",
        user_message=(
            "Capek banget ikut organisasi kampus sekarang, rapatnya kebanyakan pas "
            "lagi deket-deket ujian. Kadang aku mikir mendingan keluar aja tapi "
            "takut dibilang gak komit."
        ),
    ),
    DialogueScenario(
        id="rm1_career",
        domain="career_transition",
        user_id=ARYA_ID,
        memory_condition="cold_start",
        user_message=(
            "Bingung banget abis lulus nanti mau kerja di bidang apa, magang "
            "kemarin aja susah dapetnya. Rasanya semua orang udah punya arah, aku "
            "doang yang masih bingung."
        ),
    ),
    DialogueScenario(
        id="rm1_academic_memory_1",
        domain="academic",
        user_id=BUDI_ID,
        memory_condition="rich_memory",
        user_message=(
            "Tadi abis chat sama temen sekelompok, katanya validasi data emang "
            "kritis buat sidang nanti. Jadi kepikiran lagi soal bab 3 yang kemarin "
            "ditolak dosen pembimbingku."
        ),
    ),
    DialogueScenario(
        id="rm1_academic_memory_2",
        domain="academic",
        user_id=BUDI_ID,
        memory_condition="rich_memory",
        user_message=(
            "Aku coba lagi buka laptop buat lanjutin revisi, tapi begitu liat "
            "komentar dosen pembimbing di draftnya langsung pengen nutup lagi."
        ),
    ),
    DialogueScenario(
        id="rm1_academic_memory_3",
        domain="academic",
        user_id=BUDI_ID,
        memory_condition="rich_memory",
        user_message=(
            "Menurutmu kenapa ya aku selalu ngerasa dosen pembimbingku gak suka "
            "sama kerjaanku? Padahal temen-temen bilang emang wajar dapat revisi."
        ),
    ),
)


def _ensure_session(user_id: str, session_id: str) -> None:
    conn = psycopg2.connect(CONFIG.database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_sessions (id, user_id, channel, status) "
                "VALUES (%s, %s, 'text', 'active') ON CONFLICT (id) DO NOTHING",
                (session_id, user_id),
            )
            conn.commit()
    finally:
        conn.close()


def _insert_message(session_id: str, user_id: str, content: str) -> str:
    message_id = str(uuid.uuid4())
    conn = psycopg2.connect(CONFIG.database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (id, session_id, user_id, role, content, turn_index) "
                "VALUES (%s, %s, %s, 'user', %s, 1)",
                (message_id, session_id, user_id, content),
            )
            conn.commit()
    finally:
        conn.close()
    return message_id


def _cleanup_session(session_id: str) -> None:
    conn = psycopg2.connect(CONFIG.database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM agentic_graph_audits WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM guardrail_events WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
            conn.commit()
    finally:
        conn.close()


async def _get_axis_reply(scenario: DialogueScenario) -> str:
    os.environ["LLM_PROVIDER"] = "gemini"
    from agentic.gateway.service.chat_graph import ChatGraphService
    from agentic.gateway.model import ChatMessage, ChatTurnRequest

    ChatGraphService.draw_graph_image = lambda self: None
    service = ChatGraphService()
    await service._get_graph()

    session_id = str(uuid.uuid4())
    _ensure_session(scenario.user_id, session_id)
    message_id = _insert_message(session_id, scenario.user_id, scenario.user_message)
    try:
        request = ChatTurnRequest(
            user_id=scenario.user_id,
            session_id=session_id,
            current_message_id=message_id,
            current_message=scenario.user_message,
            messages=[ChatMessage(role="user", content=scenario.user_message)],
            session_turn=1,
            language_pref="id",
            phq9_state=None,
            cbt_state=None,
            include_state=True,
            confession_mode=False,
        )
        response = await service.invoke(request)
        return response.reply
    finally:
        _cleanup_session(session_id)


def _get_baseline_reply(scenario: DialogueScenario) -> str:
    memory_enabled = scenario.memory_condition == "rich_memory"
    result = baseline_turn(
        user_id=scenario.user_id,
        user_message=scenario.user_message,
        memory_enabled=memory_enabled,
        config=CONFIG,
    )
    return result.reply


def _judge_call(model: str, prompt: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=800),
    )
    raw = (getattr(response, "text", "") or "").strip()
    if raw.startswith("```"):
        _, _, rest = raw.partition("```")
        if rest.startswith("json"):
            rest = rest[4:]
        raw = rest.rstrip("`").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    payload = match.group(0) if match else raw
    return json.loads(payload)


JUDGE_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash-lite"]


async def main() -> None:
    from agentic.memory.neo4j_client import init_client

    await init_client()

    random.seed(20260714)
    rows: list[dict[str, Any]] = []

    for scenario in SCENARIOS:
        print(f"\n{'#'*70}\n{scenario.id} ({scenario.domain}, {scenario.memory_condition})\n{'#'*70}")
        axis_reply = await _get_axis_reply(scenario)
        print(f"AXIS: {axis_reply[:200]}")
        baseline_reply = await asyncio.to_thread(_get_baseline_reply, scenario)
        print(f"Baseline: {baseline_reply[:200]}")

        axis_is_a = random.random() < 0.5
        response_a = axis_reply if axis_is_a else baseline_reply
        response_b = baseline_reply if axis_is_a else axis_reply

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            rubric=RUBRIC,
            user_message=scenario.user_message,
            response_a=response_a,
            response_b=response_b,
        )

        judge_results: dict[str, Any] = {}
        for model in JUDGE_MODELS:
            for attempt in range(3):
                try:
                    judge_results[model] = _judge_call(model, prompt)
                    break
                except Exception as exc:
                    print(f"  judge {model} attempt {attempt+1} failed: {exc}")
                    time.sleep(2)
            else:
                judge_results[model] = None

        rows.append({
            "scenario": scenario.id,
            "domain": scenario.domain,
            "memory_condition": scenario.memory_condition,
            "axis_is_a": axis_is_a,
            "user_message": scenario.user_message,
            "axis_reply": axis_reply,
            "baseline_reply": baseline_reply,
            "judge_results": judge_results,
        })

    out_dir = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm1_dialogue"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "raw_results.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\nSaved raw results to {out_dir / 'raw_results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
