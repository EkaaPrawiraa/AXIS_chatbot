"""Internal helpers for the read-side."""

from __future__ import annotations


# Same closed set as kg_writer (and kg_deleter). Duplicated rather than
# imported to keep the dependency direction pointing the right way:
# retriever does not depend on kg_writer.
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
    """Raise unless ``label`` is in the read allow-list."""
    if label not in DERIVED_LABELS:
        raise ValueError(
            f"label {label!r} not in retriever allow-list {sorted(DERIVED_LABELS)}"
        )
    return label


# Standard fragment to filter out invalidated edges and deactivated
# nodes. Callers append this to their MATCH WHERE clause.
ALIVE_EDGE_FILTER = "r.t_invalid IS NULL"
ALIVE_NODE_FILTER = "coalesce(n.active, true) = true"
