"""skipped"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Distortion:
    name: str                       # canonical key (matches KG schema)
    label_id: str
    label_en: str
    cues_id: tuple[str, ...]
    cues_en: tuple[str, ...]
    socratic_id: str
    socratic_en: str

    def cue_match(self, lower_text: str) -> bool:
        return any(c in lower_text for c in self.cues_id) or any(
            c in lower_text for c in self.cues_en
        )

    def socratic(self, language: str) -> str:
        return self.socratic_id if language == "id" else self.socratic_en



_RAW_DISTORTIONS: tuple[Distortion, ...] = (
    Distortion(
        name="catastrophizing",
        label_id="bencana",
        label_en="catastrophizing",
        cues_id=(
            "pasti gagal",
            "udah hancur",
            "ga ada harapan",
            "gak ada harapan",
            "tidak ada harapan",
            "kiamat",
            "berakhir hancur",
        ),
        cues_en=("worst case", "everything is ruined", "disaster"),
        socratic_id=(
            "Kalau dipikir lagi, seberapa besar kemungkinan skenario "
            "terburuknya benar-benar terjadi?"
        ),
        socratic_en=(
            "If you step back, how likely is the worst-case scenario "
            "to actually unfold?"
        ),
    ),
    Distortion(
        name="all_or_nothing",
        label_id="hitam-putih",
        label_en="all or nothing",
        # skip overgeneralization
        cues_id=(
            "harus sempurna",
            "atau tidak sama sekali",
            "ga ada di tengah",
            "ga ada gunanya",
            "tidak bisa apa-apa",
            "ga bisa apa-apa",
            "tidak ada gunanya",
        ),
        cues_en=(
            "totally fail",
            "completely useless",
            "all or nothing",
            "cant do anything",
        ),
        socratic_id=(
            "Apakah ada area abu-abu yang mungkin terlewat di sini?"
        ),
        socratic_en="Is there a middle ground you might be missing here?",
    ),
    Distortion(
        name="mind_reading",
        label_id="membaca pikiran",
        label_en="mind reading",
        cues_id=("dia pasti benci", "mereka pikir", "pasti ga suka"),
        cues_en=("they hate me", "they must think", "everyone thinks"),
        socratic_id=(
            "Apa bukti langsung bahwa orang itu memikirkan hal tersebut?"
        ),
        socratic_en="What direct evidence shows they are thinking that?",
    ),
    Distortion(
        name="fortune_telling",
        label_id="meramal",
        label_en="fortune telling",
        cues_id=("pasti bakal", "ga akan berhasil", "udah pasti gagal", "pasti gagal"),
        cues_en=("it will fail", "i know it wont work", "i will definitely fail"),
        socratic_id=(
            "Apa yang membuat kamu yakin akan terjadi seperti itu?"
        ),
        socratic_en="What makes you certain it will turn out that way?",
    ),
    Distortion(
        name="emotional_reasoning",
        label_id="penalaran emosi",
        label_en="emotional reasoning",
        cues_id=("aku merasa jadi pasti", "feel kalau aku gagal", "rasanya jadi"),
        cues_en=("i feel useless so i must be", "if i feel it its true"),
        socratic_id=(
            "Apakah perasaan ini sama dengan fakta tentang situasinya?"
        ),
        socratic_en="Is the feeling the same as the fact of the situation?",
    ),
    Distortion(
        name="should_statements",
        label_id="seharusnya",
        label_en="should statements",
        cues_id=("seharusnya", "harusnya udah", "wajib"),
        cues_en=("i should", "i must", "i have to"),
        socratic_id=(
            "Kalau aturan itu datang dari teman dekat, apakah kamu masih "
            "akan menerapkannya seketat itu?"
        ),
        socratic_en=(
            "If a close friend held this rule, would you apply it as "
            "strictly to them?"
        ),
    ),
    Distortion(
        name="labeling",
        label_id="pelabelan",
        label_en="labeling",
        cues_id=(
            "aku bodoh", "aku gagal", "aku payah",
            "aku tidak berguna", "tidak berguna", "ngerasa ga berguna",
            "aku emang ga berguna",
        ),
        cues_en=("i am stupid", "i am a failure", "i am worthless", "i am useless"),
        socratic_id=(
            "Apakah label ini menggambarkan satu peristiwa atau "
            "keseluruhan dirimu?"
        ),
        socratic_en="Does this label describe one event or your whole self?",
    ),
    Distortion(
        name="magnification",
        label_id="pembesaran",
        label_en="magnification",
        cues_id=("ini parah banget", "udah ngga ketolong", "fatal"),
        cues_en=("this is terrible", "this is the end of"),
        socratic_id=(
            "Seberapa besar pengaruh kejadian ini dalam satu minggu lagi?"
        ),
        socratic_en=(
            "How big a deal will this still feel a week from now?"
        ),
    ),
    Distortion(
        name="personalization",
        label_id="personalisasi",
        label_en="personalization",
        cues_id=("ini salahku", "gara-gara aku", "karena aku"),
        cues_en=("its my fault", "i caused this"),
        socratic_id=(
            "Faktor lain apa yang juga ikut berperan dalam situasi ini?"
        ),
        socratic_en=(
            "What other factors may have contributed to this situation?"
        ),
    ),
    Distortion(
        name="overgeneralization",
        label_id="generalisasi",
        label_en="overgeneralization",
        # patterns belong here
        cues_id=(
            "selalu",
            "tidak pernah",
            "selalu kayak gini",
            "tiap kali pasti",
            "semuanya selalu",
        ),
        cues_en=(
            "always",
            "never",
            "always like this",
            "this always happens",
        ),
        socratic_id=(
            "Pernahkah ada saat hasilnya berbeda dari pola ini?"
        ),
        socratic_en="Has there been a time the outcome was different?",
    ),
)


DISTORTIONS: dict[str, Distortion] = {d.name: d for d in _RAW_DISTORTIONS}



def detect_distortion_in_text(text: str) -> Distortion | None:
    """None"""
    if not text:
        return None
    lowered = text.lower()
    for d in DISTORTIONS.values():
        if d.cue_match(lowered):
            return d
    return None


__all__ = ["Distortion", "DISTORTIONS", "detect_distortion_in_text"]
