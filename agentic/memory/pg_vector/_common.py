"""validate & map lbl-to-table"""

from __future__ import annotations


# buat nyimpan mapping.

LABEL_TO_TABLE: dict[str, str] = {
    "Memory":     "memory_embeddings",
    "Experience": "experience_embeddings",
    "Thought":    "thought_embeddings",
    "Trigger":    "trigger_embeddings",
    "Behavior":   "behavior_embeddings",
}

EMBEDDABLE_LABELS: frozenset[str] = frozenset(LABEL_TO_TABLE.keys())


def table_for(label: str) -> str:
    """resolve node to pgvector table"""
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
    """reject w/o match."""
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
    """serialize float list to pgvector format"""
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
