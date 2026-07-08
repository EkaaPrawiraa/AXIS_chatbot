"""shared validate & map lbl-to-table for pgvector adapter"""

from __future__ import annotations


# buat nyimpen mapping label table.

LABEL_TO_TABLE: dict[str, str] = {
    "Memory":     "memory_embeddings",
    "Experience": "experience_embeddings",
    "Thought":    "thought_embeddings",
    "Trigger":    "trigger_embeddings",
    "Behavior":   "behavior_embeddings",
}

EMBEDDABLE_LABELS: frozenset[str] = frozenset(LABEL_TO_TABLE.keys())


def table_for(label: str) -> str:
    """resolve node label to pgvector mirror table name"""
    if label not in LABEL_TO_TABLE:
        raise ValueError(
            f"label {label!r} is not embeddable. "
            f"Allowed: {sorted(EMBEDDABLE_LABELS)}"
        )
    return LABEL_TO_TABLE[label]



def require_str(value: str | None, field_name: str) -> str:
    """check null"""
    if value is None or not str(value).strip():
        raise ValueError(f"Required field '{field_name}' is None or empty")
    return value


def require_vector(vec: list[float] | None, expected_dim: int) -> list[float]:
    """reject embeddings w/o matching dim."""
    if vec is None:
        raise ValueError("embedding vector is required (got None)")
    if not isinstance(vec, list):
        raise ValueError(
            f"embedding must be list[float], got {type(vec).__name__}"
        )
    if len(vec) != expected_dim:
        raise ValueError(
            f"embedding has length {len(vec)}, expected {expected_dim}"
        )
    return vec


def vector_literal(vec: list[float]) -> str:
    """serialize list[float] to pgvector format"""
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
