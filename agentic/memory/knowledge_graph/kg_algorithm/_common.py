"""helper func"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    """`get now`"""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """uuid4 = uuid4.toString(); id = uuid4;"""
    return str(uuid.uuid4())


def _require(value: Any, field_name: str) -> Any:
    """null check 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22"""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Required field '{field_name}' is None or empty")
    return value
