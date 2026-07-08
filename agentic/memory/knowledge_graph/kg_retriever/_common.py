"""read-side helpers"""

from __future__ import annotations


# retriever, kg_writer.
DERIVED_LABELS: frozenset[str] = frozenset({
    "Experience",
    "Emotion",
    "Thought",
    "Trigger",
    "Behavior",
    "Subject",   # primary label (renamed from Person)
    "Person",    # kept for backward compat — old :Person nodes may still exist in DB
    "Memory",
})


def validate_label(label: str) -> str:
    """raise unless 'label' in allow-list"""
    if label not in DERIVED_LABELS:
        raise ValueError(
            f"label {label!r} not in retriever allow-list {sorted(DERIVED_LABELS)}"
        )
    return label


# filter edges, deactivate nodes, MATCH WHERE
ALIVE_EDGE_FILTER = "r.t_invalid IS NULL"
ALIVE_NODE_FILTER = "coalesce(n.active, true) = true"
