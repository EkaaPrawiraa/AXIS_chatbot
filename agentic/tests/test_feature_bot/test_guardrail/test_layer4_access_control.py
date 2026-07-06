"""
Tests for Layer 4 KG access control (sensitivity policy + suppression).
"""

from __future__ import annotations

import pytest

from agentic.memory.access_control import (
    MemoryCandidate,
    apply_sensitivity_policy,
    load_policy,
    serialize_block,
)


def _candidate(
    *,
    id_: str = "m1",
    level: int = 0,
    content: str = "hari ini aku ngerjain skripsi",
    summary: str | None = None,
    category: str | None = None,
    importance: float = 1.0,
    suppressed: bool = False,
    valid: bool = True,
) -> MemoryCandidate:
    return MemoryCandidate(
        id=id_,
        sensitivity_level=level,
        content=content,
        summary=summary,
        category=category,
        importance=importance,
        suppressed=suppressed,
        valid=valid,
    )


class TestPolicyLoading:
    def test_loads_four_tiers(self) -> None:
        policy = load_policy(force_reload=True)
        for level in (0, 1, 2, 3):
            assert level in policy.tiers, f"missing tier {level}"
        assert policy.tiers[3].retrieval == "category_only"
        assert policy.tiers[2].retrieval == "summary_only"

    def test_invariants_default_to_true(self) -> None:
        policy = load_policy()
        assert policy.suppress_flag_required is True
        assert policy.bitemporal_validity_required is True
        assert policy.user_override_honored is True


class TestPolicyApplication:
    @pytest.mark.asyncio
    async def test_level_0_full_text(self, audit) -> None:
        items = [_candidate(level=0, content="kerja kelompok lancar")]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert len(out) == 1
        assert out[0].mode == "full_text"
        assert out[0].text == "kerja kelompok lancar"
        # No redaction event for full text.
        assert not any(e.event_type == "redacted_memory" for e in audit.events)

    @pytest.mark.asyncio
    async def test_level_2_summary_only(self, audit) -> None:
        items = [
            _candidate(
                level=2,
                content="cerita panjang yang sensitif",
                summary="rasa cemas berulang sebelum ujian",
                category="anxiety",
            ),
        ]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert len(out) == 1
        assert out[0].mode == "summary_only"
        assert "cerita panjang" not in out[0].text
        assert any(e.event_type == "redacted_memory" for e in audit.events)

    @pytest.mark.asyncio
    async def test_level_3_category_only(self, audit) -> None:
        items = [
            _candidate(
                level=3,
                content="detail traumatis yang seharusnya tidak diulang",
                category="self_harm_history",
            ),
        ]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert len(out) == 1
        assert out[0].mode == "category_only"
        assert "detail traumatis" not in out[0].text
        assert "self_harm_history" in out[0].text

    @pytest.mark.asyncio
    async def test_invalid_node_blocked(self, audit) -> None:
        items = [_candidate(valid=False)]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert out == ()
        assert any(e.event_type == "invalid_skipped" for e in audit.events)

    @pytest.mark.asyncio
    async def test_user_suppression_blocked(self, audit) -> None:
        items = [_candidate(suppressed=True)]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert out == ()
        assert any(
            e.event_type == "user_suppressed_skipped" for e in audit.events
        )

    @pytest.mark.asyncio
    async def test_importance_floor_filters(self, audit) -> None:
        # Level 3 floor is 0.8; importance 0.5 should be filtered.
        items = [_candidate(level=3, importance=0.5, category="trauma")]
        out = await apply_sensitivity_policy(items, audit=audit)
        assert out == ()

    @pytest.mark.asyncio
    async def test_max_items_cap(self, audit) -> None:
        items = [_candidate(id_=f"m{i}", level=0) for i in range(20)]
        out = await apply_sensitivity_policy(items, audit=audit)
        # Tier 0 cap is 5.
        assert len(out) <= 5


class TestSerialize:
    def test_block_groups_modes(self) -> None:
        from agentic.memory.access_control import RenderedMemory

        items = (
            RenderedMemory(id="a", text="ngerjain skripsi", mode="full_text",
                           sensitivity_level=0),
            RenderedMemory(id="b", text="rasa cemas berulang",
                           mode="summary_only", sensitivity_level=2),
            RenderedMemory(
                id="c",
                text="Catatan sensitif tercatat (kategori: trauma).",
                mode="category_only",
                sensitivity_level=3,
            ),
        )
        block = serialize_block(items)
        assert "## Konteks dari percakapan sebelumnya:" in block
        assert "## Pola emosional yang tercatat (ringkasan saja):" in block
        assert "## Catatan sensitif" in block
