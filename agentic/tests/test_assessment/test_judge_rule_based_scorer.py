"""Regression tests for the rule-based fast path in `judge.py`.

Guards against the prefix-match over-reach found in
docs/importantS/analisis_phq9_subgraph.md (Temuan #1): a long free-text
reply that merely opens with a word that is also a canonical option
label ("kadang", "sering", "jarang", "selalu", "tidak") must NOT get a
score locked in from that one word alone -- it has to fall through to
the full LLM judge, which sees the whole sentence and the scoring
rubric. This matters most on item 9 (self-harm ideation), where a
qualifier later in the sentence changes the meaning entirely.
"""

from agentic.agent.phq9.judge import _rule_based_score


def test_long_freetext_opening_with_canonical_word_is_not_locked():
    reply = (
        "kadang kepikiran juga sih pengen ngilang aja gitu, tapi ga "
        "sampe niat ngapa-ngapain"
    )
    score, confidence = _rule_based_score(reply, "id")
    assert score is None
    assert confidence == 0.0


def test_long_freetext_with_qualifier_is_not_locked_by_first_word():
    reply = "tidak, maksudnya bukan gitu, aku cuma capek doang bukan mikir yang aneh aneh"
    score, confidence = _rule_based_score(reply, "id")
    assert score is None
    assert confidence == 0.0


def test_casual_sentence_with_context_falls_through_to_llm():
    reply = "lumayan sering sih akhir-akhir ini, apalagi pas lagi banyak deadline"
    score, confidence = _rule_based_score(reply, "id")
    assert score is None
    assert confidence == 0.0


def test_short_filler_after_label_still_matches_deterministically():
    """A label plus a couple of short filler words is still a direct pick."""
    for reply, expected_score in [
        ("kadang deh", 1),
        ("kadang sih", 1),
        ("ga sama sekali sih", 0),
        ("sering banget", 2),
    ]:
        score, confidence = _rule_based_score(reply, "id")
        assert score == expected_score, f"{reply!r} -> {score!r}"
        assert confidence == 0.95


def test_exact_canonical_labels_still_match_at_full_confidence():
    for reply, expected_score in [
        ("kadang-kadang", 1),
        ("tidak sama sekali", 0),
        ("hampir setiap hari", 3),
        ("selalu", 3),
    ]:
        score, confidence = _rule_based_score(reply, "id")
        assert score == expected_score
        assert confidence == 1.0


def test_bare_digit_still_matches():
    score, confidence = _rule_based_score("2", "id")
    assert score == 2
    assert confidence == 1.0


def test_unmatched_reply_returns_none():
    score, confidence = _rule_based_score("random unrelated text", "id")
    assert score is None
    assert confidence == 0.0
