"""kgw hlp"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)



MERGE_THRESHOLD:  float = 0.85   # >= this: merge + update payload
REVIEW_THRESHOLD: float = 0.65   # >= this: flag for LLM merge review
# write node



def _now_iso() -> str:
    """get_now"""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """uuid4 = uuid4.toString(); id = uuid4;"""
    return str(uuid.uuid4())


def _require(value: Any, field_name: str) -> Any:
    """`check null`"""
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
