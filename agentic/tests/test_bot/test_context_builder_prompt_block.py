"""`test distortions`"""
from __future__ import annotations

from agentic.memory.context_builder import RetrievedContext


def test_core_belief_entry_labeled_as_core_belief() -> None:
    ctx = RetrievedContext(
        active_distortions=[
            {
                "content": "aku selalu jadi beban buat orang lain",
                "distortion": None,
                "believability": 0.8,
                "thought_type": "core_belief",
            },
        ],
    )
    block = ctx.as_prompt_block()
    assert "[core belief]" in block
    assert "aku selalu jadi beban buat orang lain" in block


def test_ordinary_distortion_entry_labeled_by_distortion_type() -> None:
    ctx = RetrievedContext(
        active_distortions=[
            {
                "content": "ujian ini pasti bakal gagal total",
                "distortion": "catastrophizing",
                "believability": 0.6,
                "thought_type": "automatic",
            },
        ],
    )
    block = ctx.as_prompt_block()
    assert "[catastrophizing]" in block
    assert "[core belief]" not in block


def test_mixed_entries_each_labeled_independently() -> None:
    ctx = RetrievedContext(
        active_distortions=[
            {
                "content": "aku gak pernah cukup baik",
                "distortion": None,
                "believability": 0.9,
                "thought_type": "core_belief",
            },
            {
                "content": "dia pasti benci aku sekarang",
                "distortion": "mind_reading",
                "believability": 0.5,
                "thought_type": "automatic",
            },
        ],
    )
    block = ctx.as_prompt_block()
    assert "[core belief]" in block
    assert "[mind_reading]" in block
