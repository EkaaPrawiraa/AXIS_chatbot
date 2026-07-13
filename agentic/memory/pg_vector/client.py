"""skip klo error"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PgvectorConfig:
    host:     str = "localhost"
    port:     int = 5432
    user:     str = "companion"
    password: str = "devpassword"
    database: str = "companion_chatbot"
    min_size: int = 1
    max_size: int = 10

    @classmethod
    def from_env(cls) -> "PgvectorConfig":
        return cls(
            host     = os.getenv("PG_HOST", "localhost"),
            port     = int(os.getenv("PG_PORT", "5432")),
            user     = os.getenv("PG_USER", "companion"),
            password = os.getenv("PG_PASSWORD", "devpassword"),
            database = os.getenv("PG_DATABASE", "companion_chatbot"),
            min_size = int(os.getenv("PG_POOL_MIN_SIZE", "1")),
            max_size = int(os.getenv("PG_POOL_MAX_SIZE", "10")),
        )


_pool = None
_unavailable: bool = False


async def get_pool():
    """None"""
    global _pool, _unavailable

    if _pool is not None:
        return _pool
    if _unavailable:
        return None

    try:
        import asyncpg  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "asyncpg not installed; pg_vector running in offline mode. "
            "Install with: pip install asyncpg"
        )
        _unavailable = True
        return None

    cfg = PgvectorConfig.from_env()
    try:
        _pool = await asyncpg.create_pool(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            database=cfg.database,
            min_size=cfg.min_size,
            max_size=cfg.max_size,
        )
        logger.info(
            "pgvector pool ready (host=%s db=%s, min=%d max=%d)",
            cfg.host, cfg.database, cfg.min_size, cfg.max_size,
        )
        return _pool
    except Exception as exc:
        logger.warning(
            "pgvector pool unavailable: %s. "
            "Semantic retrieval and embedding upserts will no-op.",
            exc,
        )
        _unavailable = True
        return None


async def close_pool() -> None:
    """close pool. safe to call."""
    global _pool, _unavailable
    if _pool is not None:
        try:
            await _pool.close()
        finally:
            _pool = None
    _unavailable = False


async def is_available() -> bool:
    """skip except"""
    pool = await get_pool()
    return pool is not None

async def get_neo4j():
    if not os.getenv("NEO4J_PASSWORD"):
        return None
    try:
        from neo4j import AsyncGraphDatabase  # type: ignore[import-not-found]

        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD"),
            ),
            max_connection_pool_size=int(os.getenv("NEO4J_POOL_SIZE", "20")),
        )
        await driver.verify_connectivity()
        return driver
    except Exception as exc:
        logger.warning(
            "neo4j unavailable: %s"
            "Knowledge Graph will no-op.", 
            exc)
        return None