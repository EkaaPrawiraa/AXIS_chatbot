"""Shared helpers for the deleter package."""

from __future__ import annotations


DERIVED_LABELS: frozenset[str] = frozenset({
    "Experience",
    "Emotion",
    "Thought",
    "Trigger",
    "Behavior",
    "Subject",
    "Person",    # kept for backward compat with existing data
    "Memory",
})


def validate_label(label: str) -> str:
    """Raise unless ``label`` is in the deleter allow-list."""
    if label not in DERIVED_LABELS:
        raise ValueError(
            f"label {label!r} not in deleter allow-list {sorted(DERIVED_LABELS)}"
        )
    return label
