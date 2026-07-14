"""Re-run only the LLM-judge step against the already-generated AXIS/baseline
replies saved by rm1_dialogue_judge.py -- avoids re-spending real API calls on
response generation when only the judge call needs fixing.

Run from repo root: .venv/bin/python3 docs/thesis_latex/evaluasi_v2/scripts/rm1_rejudge.py
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]


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

RESULTS_PATH = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm1_dialogue" / "raw_results.json"

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

Konteks yang SAH diketahui kedua sistem sebelum merespons (bukan halusinasi
jika dipakai): nama panggilan pengguna adalah "{display_name}". {memory_note}

Konteks pengguna (pesan yang sedang dibalas):
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
bukan panjang teks. PENTING: jawab HANYA dengan satu baris JSON valid (tanpa newline
di dalam string manapun, tanpa markdown fence, tanpa teks lain sebelum atau sesudah),
persis format berikut:

{{"scores_a": {{"reaksi_emosional": 0, "interpretasi_konteks": 0, "eksplorasi": 0, "ketepatan_cbt": 0, "batas_non_klinis": 0, "kesesuaian_bahasa": 0, "groundedness": 0}}, "scores_b": {{"reaksi_emosional": 0, "interpretasi_konteks": 0, "eksplorasi": 0, "ketepatan_cbt": 0, "batas_non_klinis": 0, "kesesuaian_bahasa": 0, "groundedness": 0}}, "preference": "A", "reason": "max 12 words, no quotes or newlines"}}
"""

JUDGE_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash-lite"]


def _judge_call(model: str, prompt: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2000),
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


DISPLAY_NAME = {"cold_start": "Arya", "rich_memory": "Budi"}
MEMORY_NOTE = {
    "cold_start": (
        "Sistem TIDAK memiliki memori jangka panjang tentang pengguna ini "
        "(pengguna baru) - beri skor groundedness netral (1) untuk kedua "
        "respons kecuali salah satunya mengklaim detail personal spesifik "
        "yang jelas tidak berdasar (bukan sekadar menyebut nama)."
    ),
    "rich_memory": (
        "Sistem MEMILIKI memori jangka panjang yang sah tentang pengguna ini: "
        "skripsi bab 3 pernah ditolak dosen pembimbing, kecemasan terkait "
        "bimbingan, kecenderungan menghindar membuka laptop. Merujuk detail "
        "ini BUKAN halusinasi, itu penggunaan memori yang benar - beri skor "
        "groundedness tinggi untuk respons yang merujuknya secara akurat, "
        "dan lebih rendah bila detail yang dirujuk TIDAK sesuai fakta di atas."
    ),
}


def main() -> None:
    rows = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    for row in rows:
        print(f"\n{'#'*70}\n{row['scenario']}\n{'#'*70}")
        axis_is_a = row["axis_is_a"]
        response_a = row["axis_reply"] if axis_is_a else row["baseline_reply"]
        response_b = row["baseline_reply"] if axis_is_a else row["axis_reply"]
        mem_cond = row["memory_condition"]

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            rubric=RUBRIC,
            display_name=DISPLAY_NAME[mem_cond],
            memory_note=MEMORY_NOTE[mem_cond],
            user_message=row["user_message"],
            response_a=response_a,
            response_b=response_b,
        )

        judge_results: dict[str, Any] = {}
        for model in JUDGE_MODELS:
            for attempt in range(3):
                try:
                    judge_results[model] = _judge_call(model, prompt)
                    print(f"  {model}: OK -> preference={judge_results[model].get('preference')}")
                    break
                except Exception as exc:
                    print(f"  judge {model} attempt {attempt+1} failed: {exc}")
                    time.sleep(3)
            else:
                judge_results[model] = None
        row["judge_results"] = judge_results

    RESULTS_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nUpdated {RESULTS_PATH}")


if __name__ == "__main__":
    main()
