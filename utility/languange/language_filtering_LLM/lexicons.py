"""Lexicons and seed lists for filtering and scoring."""

from __future__ import annotations

# Common Indonesian/English stopwords to down-rank obvious function words.
STOPWORDS = {
    "dan", "yang", "di", "ke", "dari", "atau", "untuk", "pada", "itu", "ini",
    "the", "a", "an", "to", "of", "in", "on", "at", "for", "with", "is", "are",
}

# Slang and informal markers commonly used by Indonesian students.
SLANG_MARKERS = {
    "gw", "gue", "gua", "lu", "lo", "kak", "bro", "sis", "wkwk", "haha", "lol",
    "bgt", "banget", "gk", "ga", "nggak", "gpp", "gws", "btw", "idk",
    # L1 emotional slang (docs.md examples)
    "gabut", "mager", "galau", "baper", "kzl", "capek",
    # Common Indo-English emotional borrowings
    "down", "cringe",
}

# Mental health related seed lexicon (Indonesian + English).
MENTAL_HEALTH_SEEDS = {
    "stress", "stres", "burnout", "depresi", "depressed", "anxiety", "anxious",
    "panic", "panik", "trauma", "overthinking", "overthink", "insecure",
    # L2 informal mental-health terms (docs.md examples)
    "healing", "toxic", "trigger",
    # L3 code-switch emotional phrases (docs.md examples)
    "feel guilty", "guilty", "lost", "not okay", "i'm not okay",
    # L4 euphemisms / hidden distress indicators (docs.md examples)
    "capek sama semuanya", "nggak tau mau ngapain lagi",
    "udah nggak mau ngapa-ngapain", "udah gak mau ngapa-ngapain",
    "kayak nggak ada pointnya", "kayak gak ada pointnya",
    "pengen ngilang", "mending gue nggak ada aja", "mending gue gak ada aja",
    "capek hidup", "capek", "hampa", "kosong", "self-harm", "self harm",
    "hurt", "hopeless", "putus asa", "ga guna", "gak ada gunanya",
}

# Patterns indicating slang or informal writing.
SLANG_PATTERNS = [
    r"\b(gk|ga|nggak|bgt|bngt|bgtu|gpp|wkwk|wk\b)",
    r"[a-z]{1,}\d+",  # alphanumeric slang like bgt2
    r"\w{2,}(h|w|x){2,}$",  # elongated endings (yahhh, wkwkwk)
]

# Patterns indicating mental-health context in examples or definitions.
MENTAL_PATTERNS = [
    r"\b(stress|stres|burnout|depresi|panic|trauma|overthink|overthinking)\b",
    r"\b(healing|toxic|trigger)\b",
    r"\b(feel guilty|not okay|i[' ]?m not okay|lost)\b",
    r"\b(capek hidup|capek sama semuanya|putus asa|self[- ]?harm|hopeless|ga guna|gak ada gunanya)\b",
    r"\b(udah (nggak|gak) mau ngapa-ngapain|nggak tau mau ngapain lagi|kayak (nggak|gak) ada pointnya|pengen ngilang|mending gue (nggak|gak) ada aja)\b",
]
