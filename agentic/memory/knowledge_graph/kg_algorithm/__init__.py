"""buat ngambil data"""

from __future__ import annotations

from agentic.memory.knowledge_graph.kg_algorithm.supersession import supersede_thought
from agentic.memory.knowledge_graph.kg_algorithm.decay        import run_memory_decay
from agentic.memory.knowledge_graph.kg_algorithm.lifecycle import (
    deactivate_trigger,
    reappraise_experience,
    replace_behavior,
)

__all__ = [
    "supersede_thought",
    "run_memory_decay",
    "deactivate_trigger",
    "reappraise_experience",
    "replace_behavior",
]
