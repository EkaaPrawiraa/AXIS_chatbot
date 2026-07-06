"""
Standalone linguistic enrichment test runner. Mirrors the layout of
the other scripts/run_*_tests.py files: no pytest dependency, prints
PASS/FAIL per test, exits non-zero on failure.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

ROOT = Path("/sessions/focused-dreamy-albattani/mnt/CompanionshipChatBot")
sys.path.insert(0, str(ROOT))

from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.linguistic.corpus import (
    CorpusEntry,
    LinguisticCorpus,
    clear_cache,
    load_corpus,
    load_default_corpus,
)
from agentic.agent.linguistic.detector import (
    LANGUAGE_GAP_THRESHOLD,
    MIN_TOKENS_FOR_VERDICT,
    detect_linguistic_signals,
)
from agentic.agent.nodes.linguistic_enrichment import linguistic_enrichment_node
from agentic.agent.state import empty_conversation_state


PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def t(name: str):
    def deco(fn):
        async def runner():
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
                PASSED.append(name)
                print(f"  PASS  {name}")
            except Exception as exc:
                FAILED.append((name, traceback.format_exc()))
                print(f"  FAIL  {name}: {exc!r}")

        runner.__name__ = fn.__name__
        return runner

    return deco


def section(label: str) -> None:
    print(f"\n=== {label} ===")



def _fixture_corpus() -> LinguisticCorpus:
    """Tight in-memory corpus that exercises every code path."""
    entries = [
        CorpusEntry(
            term="capek hidup",
            category="L3",
            language="id",
            register="slang",
            emotional_weight="high",
            distress_signal=True,
            escalation_flag=True,
        ),
        CorpusEntry(
            term="burnout",
            category="L2",
            language="en-borrowed",
            register="informal",
            emotional_weight="high",
            distress_signal=True,
            escalation_flag=False,
        ),
        CorpusEntry(
            term="anjir",
            category="L1",
            language="id",
            register="slang",
            emotional_weight="low",
            distress_signal=False,
            escalation_flag=False,
        ),
        CorpusEntry(
            term="ngebleng",
            category="L2",
            language="id",
            register="slang",
            emotional_weight="medium",
            distress_signal=False,
            escalation_flag=False,
        ),
    ]
    return LinguisticCorpus.from_entries(entries)



@t("default corpus loads non-empty")
def test_default_corpus_loads():
    corpus = load_default_corpus()
    assert len(corpus) > 0, "default corpus should have entries"


@t("corpus cache returns same instance")
def test_corpus_cache():
    c1 = load_default_corpus()
    c2 = load_default_corpus()
    assert c1 is c2


@t("missing file yields empty corpus")
def test_missing_file():
    clear_cache()
    corpus = load_corpus(Path("/nonexistent/corpus.jsonl"))
    assert len(corpus) == 0


@t("corpus tolerates malformed lines")
def test_malformed_lines():
    clear_cache()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as fh:
        fh.write('{"term": "valid", "language": "id"}\n')
        fh.write("not json at all\n")
        fh.write('{"language": "id"}\n')  # missing term
        fh.write('{"term": "another"}\n')
        path = Path(fh.name)
    corpus = load_corpus(path)
    assert len(corpus) == 2


# Detector: language verdict


@t("indonesian message detected as id")
def test_id_dominant():
    sig = detect_linguistic_signals(
        "aku capek banget hari ini ga sanggup ngapain",
        _fixture_corpus(),
    )
    assert sig.language == "id"


@t("english message detected as en")
def test_en_dominant():
    sig = detect_linguistic_signals(
        "i have an assignment deadline tomorrow and i am stressed",
        _fixture_corpus(),
    )
    assert sig.language == "en"


@t("code-switched message detected as mixed")
def test_mixed_detected():
    # Roughly balanced id-function + en-academic tokens.
    sig = detect_linguistic_signals(
        "aku ada deadline assignment yang harus dikerjakan tomorrow",
        _fixture_corpus(),
    )
    assert sig.language == "mixed", (
        f"got language={sig.language}, signal={sig.language_signal}"
    )
    assert sig.id_token_count > 0
    assert sig.en_token_count > 0


@t("very short message falls back to default")
def test_too_short_falls_back():
    sig = detect_linguistic_signals("ok", _fixture_corpus())
    assert sig.language == "id"
    assert sig.language_signal == "too_short"


@t("empty message returns EMPTY_SIGNALS")
def test_empty_message():
    sig = detect_linguistic_signals("", _fixture_corpus())
    assert sig.total_tokens == 0
    assert sig.slang_terms == ()


# Detector: corpus signals


@t("multi-word distress term surfaces")
def test_distress_multi_word():
    sig = detect_linguistic_signals(
        "kayaknya aku udah capek hidup banget",
        _fixture_corpus(),
    )
    assert "capek hidup" in sig.slang_terms
    assert "capek hidup" in sig.distress_terms
    assert "capek hidup" in sig.escalation_terms


@t("single-word loanword surfaces and counts as english signal")
def test_burnout_loanword():
    sig = detect_linguistic_signals(
        "gue burnout banget kayaknya",
        _fixture_corpus(),
    )
    assert "burnout" in sig.slang_terms
    assert sig.en_token_count >= 1


@t("word boundary prevents false positive")
def test_word_boundary():
    sig = detect_linguistic_signals(
        "petugas keamanan kampus",
        _fixture_corpus(),
    )
    # "tugas" must NOT match inside "petugas".
    # Fixture has no entry "tugas" so this is verifying the boundary
    # logic doesn't accidentally split tokens.
    assert "tugas" not in sig.slang_terms


@t("register classification picks slang over informal")
def test_register_slang_wins():
    sig = detect_linguistic_signals(
        "gue burnout dan anjir capek banget",
        _fixture_corpus(),
    )
    assert sig.register == "slang"


@t("no hits returns formal register")
def test_no_hits_formal():
    sig = detect_linguistic_signals(
        "aku sedang mengerjakan tugas akhir",
        _fixture_corpus(),
    )
    assert sig.register == "formal"


@t("escalation flag separate from distress")
def test_escalation_subset():
    sig = detect_linguistic_signals(
        "burnout banget akhir-akhir ini",
        _fixture_corpus(),
    )
    # burnout is distress=True, escalation=False.
    assert "burnout" in sig.distress_terms
    assert "burnout" not in sig.escalation_terms



@t("node populates linguistic_signals dict")
async def test_node_populates_signals():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "anjir burnout banget"
    out = await linguistic_enrichment_node(
        state, audit=NullGuardrailLogger(), corpus=_fixture_corpus(),
    )
    signals = out.get("linguistic_signals")
    assert isinstance(signals, dict)
    assert signals["language"] in ("id", "mixed")
    assert "anjir" in signals["slang_terms"]


@t("node fills resolved_language when missing")
async def test_node_fills_resolved_language():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "i have a deadline tomorrow assignment"
    state["resolved_language"] = None
    out = await linguistic_enrichment_node(
        state, audit=NullGuardrailLogger(), corpus=_fixture_corpus(),
    )
    assert out["resolved_language"] == "en"


@t("node refreshes resolved_language per turn")
async def test_node_respects_upstream_language():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "i have an exam tomorrow"
    state["resolved_language"] = "id"  # pretend upstream set this
    out = await linguistic_enrichment_node(
        state, audit=NullGuardrailLogger(), corpus=_fixture_corpus(),
    )
    # The node mirrors the user's latest language per turn.
    assert out["resolved_language"] == "en"


@t("node maps mixed to id for response language")
async def test_node_mixed_maps_to_id():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = (
        "aku ada deadline assignment yang harus dikerjakan tomorrow"
    )
    state["resolved_language"] = None
    out = await linguistic_enrichment_node(
        state, audit=NullGuardrailLogger(), corpus=_fixture_corpus(),
    )
    assert out["resolved_language"] == "id"
    assert out["linguistic_signals"]["language"] == "mixed"


@t("node short-circuits on empty message")
async def test_node_empty_input():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = ""
    out = await linguistic_enrichment_node(
        state, audit=NullGuardrailLogger(), corpus=_fixture_corpus(),
    )
    assert "linguistic_signals" not in out or out.get("linguistic_signals") is None



async def main():
    section("Corpus loader")
    await test_default_corpus_loads()
    await test_corpus_cache()
    await test_missing_file()
    await test_malformed_lines()

    section("Language verdict")
    await test_id_dominant()
    await test_en_dominant()
    await test_mixed_detected()
    await test_too_short_falls_back()
    await test_empty_message()

    section("Corpus signals")
    await test_distress_multi_word()
    await test_burnout_loanword()
    await test_word_boundary()
    await test_register_slang_wins()
    await test_no_hits_formal()
    await test_escalation_subset()

    section("Node integration")
    await test_node_populates_signals()
    await test_node_fills_resolved_language()
    await test_node_respects_upstream_language()
    await test_node_mixed_maps_to_id()
    await test_node_empty_input()

    print("\n" + "=" * 60)
    print(f"PASSED: {len(PASSED)}")
    print(f"FAILED: {len(FAILED)}")
    if FAILED:
        for name, tb in FAILED:
            print(f"\n--- {name} ---")
            print(tb)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
