"""`regression: crash on real calls`"""

from __future__ import annotations

import pytest

import agentic.memory.context_builder as context_builder_module
from agentic.memory.pg_vector import SearchHit


@pytest.mark.asyncio
async def test_vector_only_mode_extracts_content_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(context_builder_module, "RETRIEVAL_MODE", "vector_only")

    async def fake_search_memory(user_id, embedding, *, top_k, min_similarity):
        return [
            SearchHit(
                neo4j_node_id="mem-1",
                content="Pengguna cemas soal sidang TA.",
                importance=0.7,
                similarity=0.81,
            )
        ]

    async def fake_search_experience(user_id, embedding, *, top_k, min_similarity):
        return [
            SearchHit(
                neo4j_node_id="exp-1",
                content="Latihan presentasi berjalan lancar.",
                importance=0.6,
                similarity=0.77,
            )
        ]

    monkeypatch.setattr(context_builder_module, "search_memory", fake_search_memory)
    monkeypatch.setattr(context_builder_module, "search_experience", fake_search_experience)

    ctx = await context_builder_module.build_context(
        user_id="u1",
        query_embedding=[0.1, 0.2, 0.3],
        query_text="gimana ya soal sidang kemarin",
    )

    assert ctx.semantic_memories == ["Pengguna cemas soal sidang TA."]
    assert ctx.semantic_experiences == ["Latihan presentasi berjalan lancar."]

    block = ctx.as_prompt_block()
    assert "Pengguna cemas soal sidang TA." in block
    assert "{'summary'" not in block  # no raw dict repr leaking into the prompt
    assert "{'description'" not in block


@pytest.mark.asyncio
async def test_vector_only_mode_survives_search_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(context_builder_module, "RETRIEVAL_MODE", "vector_only")

    async def failing_search(*args, **kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(context_builder_module, "search_memory", failing_search)
    monkeypatch.setattr(context_builder_module, "search_experience", failing_search)

    ctx = await context_builder_module.build_context(
        user_id="u1",
        query_embedding=[0.1, 0.2, 0.3],
        query_text="test",
    )

    assert ctx.semantic_memories == []
    assert ctx.semantic_experiences == []
