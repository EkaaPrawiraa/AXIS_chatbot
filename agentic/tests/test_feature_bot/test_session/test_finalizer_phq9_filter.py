import pytest

from agentic.agent.session.finalizer import SessionFinalizer


pytestmark = pytest.mark.asyncio


async def test_finalizer_does_not_write_phq9_only_session_to_longterm_memory():
    calls = {"summary": 0, "extract": 0}
    written = {}

    async def history_loader(**_kwargs):
        return [
            {
                "id": "a1",
                "role": "assistant",
                "content": "Pertanyaan 6 dari 9. Merasa buruk tentang diri sendiri, gagal, atau mengecewakan keluarga.",
                "turn_index": 1,
                "metadata": {"phq9": {"phase": "in_progress", "active_item": 6}},
            },
            {
                "id": "u1",
                "role": "user",
                "content": "Hampir setiap hari",
                "turn_index": 2,
                "metadata": {},
            },
        ]

    async def summarizer(**_kwargs):
        calls["summary"] += 1
        return "should not be called"

    async def extractor(**_kwargs):
        calls["extract"] += 1
        return {"experiences": [{"description": "should not be extracted"}]}

    async def writer(**kwargs):
        written.update(kwargs)

    finalizer = SessionFinalizer(
        history_loader=history_loader,
        summarizer=summarizer,
        extractor=extractor,
        kg_writer=writer,
    )

    result = await finalizer.finalize(session_id="s1", user_id="u1")

    assert result.ok
    assert result.summary == ""
    assert result.extracted_count == 0
    assert calls == {"summary": 0, "extract": 0}
    assert written == {}


async def test_finalizer_extracts_normal_memory_but_filters_phq9_messages():
    extracted_messages: list[str] = []
    summarized_transcripts: list[str] = []

    async def history_loader(**_kwargs):
        return [
            {
                "id": "u1",
                "role": "user",
                "content": "Aku cemas karena ujian kalkulus besok dan belum siap.",
                "turn_index": 1,
                "metadata": {},
            },
            {
                "id": "a1",
                "role": "assistant",
                "content": "Pertanyaan 1 dari 9. Sedikit minat atau kesenangan dalam melakukan aktivitas.",
                "turn_index": 2,
                "metadata": {"phq9": {"phase": "in_progress", "active_item": 1}},
            },
            {
                "id": "u2",
                "role": "user",
                "content": "Beberapa hari",
                "turn_index": 3,
                "metadata": {},
            },
        ]

    async def summarizer(*, transcript, **_kwargs):
        summarized_transcripts.append(transcript)
        return "User cemas karena ujian kalkulus besok."

    async def extractor(*, message, **_kwargs):
        extracted_messages.append(message)
        return {"experiences": [{"description": message}]}

    async def writer(**_kwargs):
        return None

    finalizer = SessionFinalizer(
        history_loader=history_loader,
        summarizer=summarizer,
        extractor=extractor,
        kg_writer=writer,
    )

    result = await finalizer.finalize(session_id="s1", user_id="u1")

    assert result.ok
    assert result.extracted_count == 1
    assert extracted_messages == [
        "Aku cemas karena ujian kalkulus besok dan belum siap."
    ]
    assert "Pertanyaan 1 dari 9" not in summarized_transcripts[0]
    assert "Beberapa hari" not in summarized_transcripts[0]
