"""Shared helpers for the kg_writer package."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)



MERGE_THRESHOLD:  float = 0.85   # >= this: merge + update payload
REVIEW_THRESHOLD: float = 0.65   # >= this: flag for LLM merge review
# < REVIEW_THRESHOLD: write a fresh node.



def _now_iso() -> str:
    """Current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Fresh UUID4 as a string. Used as the ``id`` property on every node."""
    return str(uuid.uuid4())


def _require(value: Any, field_name: str) -> Any:
    """
    Application-layer null check. Raises before any DB call is issued.

    Replaces the Enterprise-only property-existence (IS NOT NULL) constraint
    (see infra/neo4j/schema/constraints.cypher header note).
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Required field '{field_name}' is None or empty")
    return value


__all__ = [
    "MERGE_THRESHOLD",
    "REVIEW_THRESHOLD",
    "_now_iso",
    "_new_id",
    "_require",
]
