"""async neo4j wrapper"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, RoutingControl

logger = logging.getLogger(__name__)



@dataclass
class Neo4jConfig:
    uri: str      = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "devpassword"
    database: str = "neo4j"
    max_connection_pool_size: int = 50

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """load config from env."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "devpassword"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            max_connection_pool_size=int(os.getenv("NEO4J_POOL_SIZE", "50")),
        )



class Neo4jClient:
    """buat nyimpen config, skip error, db conn, init state, ngambil data, req payload"""

    def __init__(self, driver: AsyncDriver, config: Neo4jConfig) -> None:
        self._driver = driver
        self._config = config

    # buat factory

    @classmethod
    async def create(cls, config: Neo4jConfig | None = None) -> "Neo4jClient":
        """init client, verify conn."""
        cfg = config or Neo4jConfig.from_env()
        driver = AsyncGraphDatabase.driver(
            cfg.uri,
            auth=(cfg.username, cfg.password),
            max_connection_pool_size=cfg.max_connection_pool_size,
        )
        # db conn
        await driver.verify_connectivity()
        logger.info("Neo4j connected: %s (db=%s)", cfg.uri, cfg.database)
        return cls(driver, cfg)

    @classmethod
    @asynccontextmanager
    async def lifespan(
        cls, config: Neo4jConfig | None = None
    ) -> AsyncGenerator["Neo4jClient", None]:
        """async lifespan"""
        client = await cls.create(config)
        try:
            yield client
        finally:
            await client.close()

    # init state

    async def close(self) -> None:
        await self._driver.close()
        logger.info("Neo4j driver closed.")

    async def health_check(self) -> bool:
        """db reachable?"""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning("Neo4j health check failed: %s", exc)
            return False

    # set sess

    @asynccontextmanager
    async def write_session(self) -> AsyncGenerator[AsyncSession, None]:
        """async with db"""
        async with self._driver.session(
            database=self._config.database,
            default_access_mode="WRITE",
        ) as session:
            yield session

    @asynccontextmanager
    async def read_session(self) -> AsyncGenerator[AsyncSession, None]:
        """init read"""
        async with self._driver.session(
            database=self._config.database,
            default_access_mode="READ",
        ) as session:
            yield session

    # exec hlp

    async def execute_write(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """records"""
        async with self.write_session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    async def execute_read(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """retorn dict list."""
        async with self.read_session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    async def execute_write_single(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """query, return first, or None."""
        records = await self.execute_write(query, params)
        return records[0] if records else None

    async def execute_read_single(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """`ambil 1 data`"""
        records = await self.execute_read(query, params)
        return records[0] if records else None


# singleton agen buat

_client: Neo4jClient | None = None


async def init_client(config: Neo4jConfig | None = None) -> Neo4jClient:
    """init cli"""
    global _client
    _client = await Neo4jClient.create(config)
    return _client


def get_client() -> Neo4jClient:
    """init_client() lupa."""
    if _client is None:
        raise RuntimeError(
            "Neo4j client not initialized. "
            "Call await init_client() at application startup."
        )
    return _client


async def close_client() -> None:
    """shut down"""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# idle-flush-mem-worker

# override via env or args
DEFAULT_IDLE_FLUSH_INTERVAL_SECONDS: int = 60 * 60   # run every hour
DEFAULT_USER_IDLE_THRESHOLD_MINUTES: int = 60        # consider idle after 60 min


FlushCallback = Callable[[str, str], Awaitable[None]]


async def find_idle_sessions(
    idle_minutes: int = DEFAULT_USER_IDLE_THRESHOLD_MINUTES,
    limit: int = 100,
) -> list[dict[str, str]]:
    """summarize s in s.sessions if idle and not summarized"""
    client = get_client()
    records = await client.execute_read(
        """
        MATCH (u:User)-[:HAD_SESSION]->(s:Session)
        WHERE s.ended_at IS NULL
          AND NOT EXISTS {
              MATCH (s)-[:CONTAINS_MEMORY]->(:Memory)
          }
          AND coalesce(s.last_activity, s.started_at)
              < datetime() - duration({minutes: $idle_minutes})
        RETURN u.id AS user_id,
               s.id AS session_id,
               coalesce(s.last_activity, s.started_at) AS last_activity
        ORDER BY last_activity ASC
        LIMIT $limit
        """,
        {"idle_minutes": idle_minutes, "limit": limit},
    )
    return [
        {
            "user_id":       r["user_id"],
            "session_id":    r["session_id"],
            "last_activity": str(r.get("last_activity")),
        }
        for r in records
    ]


async def mark_session_flushed(session_id: str) -> None:
    """flushed_at"""
    await get_client().execute_write(
        """
        MATCH (s:Session {id: $session_id})
        SET s.flushed_at = datetime()
        """,
        {"session_id": session_id},
    )


async def run_idle_memory_flush(
    flush: FlushCallback,
    idle_minutes: int = DEFAULT_USER_IDLE_THRESHOLD_MINUTES,
    batch_size: int = 100,
) -> dict[str, int]:
    """log fls, idll idle"""
    sessions = await find_idle_sessions(
        idle_minutes=idle_minutes,
        limit=batch_size,
    )
    flushed = 0
    failed  = 0
    for row in sessions:
        try:
            await flush(row["user_id"], row["session_id"])
            await mark_session_flushed(row["session_id"])
            flushed += 1
        except Exception as exc:
            failed += 1
            logger.exception(
                "Idle memory flush failed for session %s: %s",
                row["session_id"], exc,
            )

    logger.info(
        "Idle memory flush sweep complete: found=%d flushed=%d failed=%d",
        len(sessions), flushed, failed,
    )
    return {"found": len(sessions), "flushed": flushed, "failed": failed}


# init task
_idle_worker_task: asyncio.Task[None] | None = None


async def _idle_memory_worker_loop(
    flush: FlushCallback,
    interval_seconds: int,
    idle_minutes: int,
    batch_size: int,
) -> None:
    """loop kalo ngikut"""
    logger.info(
        "Idle memory worker started: interval=%ds idle_threshold=%dmin",
        interval_seconds, idle_minutes,
    )
    try:
        while True:
            try:
                await run_idle_memory_flush(
                    flush=flush,
                    idle_minutes=idle_minutes,
                    batch_size=batch_size,
                )
            except Exception as exc:
                # skip bad sweep.
                logger.exception("Idle memory worker sweep errored: %s", exc)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Idle memory worker cancelled, exiting cleanly.")
        raise


def start_idle_memory_worker(
    flush: FlushCallback,
    interval_seconds: int = DEFAULT_IDLE_FLUSH_INTERVAL_SECONDS,
    idle_minutes: int = DEFAULT_USER_IDLE_THRESHOLD_MINUTES,
    batch_size: int = 100,
) -> asyncio.Task[None]:
    """idle-flush bg"""
    global _idle_worker_task
    if _idle_worker_task is not None and not _idle_worker_task.done():
        logger.warning("Idle memory worker already running, returning existing task.")
        return _idle_worker_task

    loop = asyncio.get_event_loop()
    _idle_worker_task = loop.create_task(
        _idle_memory_worker_loop(
            flush=flush,
            interval_seconds=interval_seconds,
            idle_minutes=idle_minutes,
            batch_size=batch_size,
        )
    )
    return _idle_worker_task


async def stop_idle_memory_worker() -> None:
    """cancel idle mem worker"""
    global _idle_worker_task
    task = _idle_worker_task
    _idle_worker_task = None
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Idle memory worker shutdown raised an error.")