"""Backward-compatibility shim for person_kg.

All logic has been moved to subject_kg.py.  Importing ``write_person`` from
this module continues to work so that existing call sites do not break until
they are migrated to ``write_subject``.
"""

from agentic.memory.knowledge_graph.kg_writer.subject_kg import write_subject as write_person  # noqa: F401

__all__ = ["write_person"]
