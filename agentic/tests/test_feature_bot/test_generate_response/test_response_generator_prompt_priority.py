from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.response_generator import _build_messages


def test_thought_record_bot_prompt_suppresses_kg_context_in_system_prompt() -> None:
    state = {
        "messages": [],
        "current_message": "Aku yakin semuanya bakal gagal.",
        "resolved_language": "id",
        "kg_context": "[Important people]\n- Ziga: supportive friend",
        "cbt_node_active": CBTTechnique.THOUGHT_RECORD.value,
        "cbt_directive": {
            "payload": {
                "bot_prompt": "Apa pikiran otomatis yang muncul saat itu?",
            },
        },
    }

    system_text = _build_messages(state)[0].content

    assert "Apa pikiran otomatis yang muncul saat itu?" in system_text
    assert "[Important people]" not in system_text
    assert "Ziga" not in system_text
