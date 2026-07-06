"""Single read/write seam for assessments and assessment-related KG."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from agentic.assessment.phq9 import (
    NUM_ITEMS,
    PHQ9Result,
    PHQ9Severity,
    to_storage_payload,
)


logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class LastPHQ9Snapshot:
    """Lightweight view used by the trigger node."""

    administered_at: datetime
    total_score: int
    severity: PHQ9Severity
    item_scores: tuple[int, ...]
    delta_from_prev: int | None = None   # positive = worsened, negative = improved


@dataclass(frozen=True)
class DistressSnapshot:
    """
    Aggregated KG distress signal.

    Attributes
    ----------
    high_distress_session_count_7d:
        Sessions in the past 7 days where the active emotion mix
        exceeded the high distress threshold.
    avg_emotion_valence_7d:
        Mean valence of emotions logged in the past 7 days.
    recurring_trigger_active:
        True when a Trigger node with frequency >= 2 was last mentioned
        (``last_seen``) within the past ``LOOKBACK_DAYS_FOR_KG`` days --
        i.e. a known stressor genuinely *reappeared* recently, not merely
        that one exists somewhere in the user's history. Triggers are
        rarely deactivated (only on explicit LLM-detected resolution),
        so without this recency bound a trigger mentioned once, months
        ago, would keep this permanently true and let Tier 2 re-offer
        PHQ-9 every RETRY_DAYS_FOR_DISTRESS days indefinitely, defeating
        the intended 14-day scheduled cadence.
    """

    high_distress_session_count_7d: int
    avg_emotion_valence_7d: float | None
    recurring_trigger_active: bool


@dataclass(frozen=True)
class AssessmentRetrySchedule:
    """When the trigger node should retry the offer."""

    user_id: str
    next_attempt_at: datetime
    reason: str


# Module-level configuration


# These are read-only thresholds used by the trigger node. They live
# here so storage queries and gate evaluation share the same constants.
HIGH_DISTRESS_VALENCE_THRESHOLD: float = -0.5
ACUTE_DISTRESS_VALENCE_THRESHOLD: float = -0.6
ACUTE_DISTRESS_INTENSITY_THRESHOLD: float = 0.7
WORSENING_DELTA_THRESHOLD: int = 3
LOOKBACK_DAYS_FOR_KG: int = 7



class AssessmentRepository:
    """
    Async repository for PHQ-9 records.

    Parameters
    ----------
    pg_pool:
        ``asyncpg.Pool`` or compatible context-managed pool. Only
        ``acquire`` and the standard execute/fetch methods are used.
    neo4j_driver:
        Optional Neo4j driver for KG-side reads. The repository can
        still operate on Postgres only when this is ``None``.
    """

    def __init__(
        self,
        *,
        pg_pool: Any,
        neo4j_driver: Any | None = None,
    ) -> None:
        self._pg = pg_pool
        self._neo4j = neo4j_driver

    # reads.

    async def get_last_phq9(self, user_id: str) -> LastPHQ9Snapshot | None:
        """Fetch the most recent PHQ-9 administration."""
        sql = (
            "SELECT administered_at, score, severity_label, "
            "       item_responses, delta_from_prev "
            "FROM assessments "
            "WHERE user_id = $1 AND instrument = 'PHQ-9' "
            "ORDER BY administered_at DESC LIMIT 1"
        )
        async with self._pg.acquire() as conn:
            row = await conn.fetchrow(sql, user_id)
        if row is None:
            return None
        raw_delta = row["delta_from_prev"]
        delta = int(raw_delta) if raw_delta is not None else None
        return LastPHQ9Snapshot(
            administered_at=_ensure_utc(row["administered_at"]),
            total_score=int(row["score"]),
            severity=PHQ9Severity(row["severity_label"]),
            item_scores=_unpack_item_scores(row["item_responses"]),
            delta_from_prev=delta,
        )

    async def get_conversation_count(self, user_id: str) -> int:
        """
        Return the number of completed conversations for ``user_id``.

        Only sessions that logged at least one turn are counted — empty or
        abandoned sessions (e.g., created then immediately navigated away)
        would skew the warm-up counter and are excluded.

        Used by ``phq9_check_node`` to enforce the cross-session warm-up
        before a first PHQ-9 offer is made to new users.
        """
        sql = (
            "SELECT COUNT(*) FROM chat_sessions "
            "WHERE user_id = $1::uuid AND turn_count > 0"
        )
        async with self._pg.acquire() as conn:
            row = await conn.fetchrow(sql, user_id)
        return int(row[0]) if row else 0

    async def get_pending_retry(
        self, user_id: str
    ) -> AssessmentRetrySchedule | None:
        """Return the active retry schedule, if any."""
        sql = (
            "SELECT user_id, next_attempt_at, reason FROM assessment_retries "
            "WHERE user_id = $1 ORDER BY next_attempt_at DESC LIMIT 1"
        )
        async with self._pg.acquire() as conn:
            row = await conn.fetchrow(sql, user_id)
        if row is None:
            return None
        return AssessmentRetrySchedule(
            user_id=row["user_id"],
            next_attempt_at=_ensure_utc(row["next_attempt_at"]),
            reason=row["reason"],
        )

    async def get_distress_snapshot(
        self, user_id: str
    ) -> DistressSnapshot:
        """
        Aggregate KG-derived distress signals over the lookback window.

        When ``neo4j_driver`` is unavailable the snapshot defaults to
        zero counts so the trigger gate falls back to the in-state
        ``emotion_pad`` only.
        """
        if self._neo4j is None:
            return DistressSnapshot(
                high_distress_session_count_7d=0,
                avg_emotion_valence_7d=None,
                recurring_trigger_active=False,
            )

        cypher = """
        MATCH (u:User {id: $user_id})
        WITH u, datetime() - duration({days: $days}) AS since
        OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
          WHERE s.started_at >= since
          OPTIONAL MATCH (s)-[:RECORDED_EMOTION]->(e:Emotion)
            WHERE e.active = true
        WITH u, since, s,
             coalesce(avg(e.valence), 0.0) AS sess_valence,
             coalesce(max(e.intensity), 0.0) AS sess_intensity
        WITH u, since,
             collect({s: s, v: sess_valence, i: sess_intensity}) AS sessions
        OPTIONAL MATCH (u)-[r:HAS_TRIGGER]->(t:Trigger)
          WHERE coalesce(t.active, true) = true
            AND coalesce(t.frequency, 0) >= $recurring_frequency
            AND t.last_seen >= since
            AND r.t_invalid IS NULL
        WITH sessions,
             count(DISTINCT t) AS recurring_trigger_count
        RETURN
          [x IN sessions WHERE x.s IS NOT NULL
              AND x.v <= $valence_th AND x.i >= $intensity_th
              | x.s.id] AS distress_session_ids,
          [x IN sessions WHERE x.s IS NOT NULL | x.v] AS valences,
          recurring_trigger_count
        """
        try:
            async with self._neo4j.session() as sess:
                record = await (
                    await sess.run(
                        cypher,
                        user_id=user_id,
                        days=LOOKBACK_DAYS_FOR_KG,
                        valence_th=HIGH_DISTRESS_VALENCE_THRESHOLD,
                        intensity_th=ACUTE_DISTRESS_INTENSITY_THRESHOLD,
                        recurring_frequency=2,
                    )
                ).single()
        except Exception as exc:
            logger.warning("distress snapshot query failed: %s", exc)
            return DistressSnapshot(
                high_distress_session_count_7d=0,
                avg_emotion_valence_7d=None,
                recurring_trigger_active=False,
            )
        if record is None:
            return DistressSnapshot(
                high_distress_session_count_7d=0,
                avg_emotion_valence_7d=None,
                recurring_trigger_active=False,
            )

        valences = [v for v in record["valences"] if v is not None]
        avg_valence = sum(valences) / len(valences) if valences else None
        return DistressSnapshot(
            high_distress_session_count_7d=len(record["distress_session_ids"]),
            avg_emotion_valence_7d=avg_valence,
            recurring_trigger_active=bool(record["recurring_trigger_count"]),
        )

    # writes.

    async def save_phq9_result(self, result: PHQ9Result) -> None:
        """
        Persist a completed PHQ-9 to BOTH Postgres and Neo4j.

        Postgres (``assessments`` table) is the source of truth for
        analytics, delta computation, and the retry scheduler.

        Neo4j (``Assessment`` node) is the source of truth for graph
        traversal: ``GetEscalationSignals`` in Go reads PHQ-9 score and
        delta directly from the graph, and the context_builder signal
        ``fetch_recurring_themes`` depends on the KG being up to date.

        Previously only Postgres was written here; Neo4j Assessment
        nodes were only created when Go called WriteAssessment — which
        required an explicit HTTP round-trip that was never wired.
        Since Python already holds a direct Neo4j connection via
        ``get_client()``, writing the Assessment node here removes that
        gap without requiring any Go involvement.
        """
        import asyncio, json, os, uuid
        from agentic.memory.neo4j_client import get_client as _neo4j_client

        payload = to_storage_payload(result)

        # 1. Postgres write.
        sql = (
            "INSERT INTO assessments "
            "(user_id, session_id, instrument, score, severity_label, "
            " item_responses, delta_from_prev, administered_at, "
            " administered_by) "
            "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)"
        )
        async with self._pg.acquire() as conn:
            await conn.execute(
                sql,
                payload["user_id"],
                payload["session_id"],
                payload["instrument"],
                payload["score"],
                payload["severity_label"],
                _to_json(payload["item_responses"]),
                payload["delta_from_prev"],
                result.administered_at,
                payload["administered_by"],
            )

        # 2. Neo4j write.
        # Mirrors what Go's WriteAssessment produces so graph traversal
        # queries (GetEscalationSignals, COMPLETED_ASSESSMENT path) work
        # without depending on a separate Go service call.
        try:
            assessment_neo4j_id = str(uuid.uuid4())
            administered_iso = (
                result.administered_at.isoformat()
                if result.administered_at
                else datetime.now(timezone.utc).isoformat()
            )
            timeout_seconds = float(
                os.getenv("PHQ9_NEO4J_WRITE_TIMEOUT_SECONDS", "3") or "3"
            )
            await asyncio.wait_for(
                _neo4j_client().execute_write(
                    """
                    MERGE (u:User {id: $user_id})
                    MERGE (s:Session {id: $session_id})
                    ON CREATE SET
                        s.user_id           = $user_id,
                        s.started_at        = datetime($administered_at),
                        s.sensitivity_level = 'normal'
                    MERGE (u)-[:HAD_SESSION]->(s)
                    CREATE (a:Assessment {
                        id:                  $a_id,
                        instrument:          $instrument,
                        score:               $score,
                        severity_label:      $severity_label,
                        delta_from_previous: $delta,
                        administered_at:     datetime($administered_at),
                        q9_score:            $q9_score,
                        item_responses:      $item_responses,
                        sensitivity_level:   'normal'
                    })
                    CREATE (u)-[:COMPLETED_ASSESSMENT {
                        t_valid:        datetime($administered_at),
                        t_invalid:      null,
                        confidence:     1.0,
                        source_session: $session_id
                    }]->(a)
                    CREATE (s)-[:PRODUCED_ASSESSMENT {
                        t_valid:        datetime($administered_at),
                        t_invalid:      null,
                        confidence:     1.0,
                        source_session: $session_id
                    }]->(a)
                    SET s.phq9_administered = true
                    """,
                    {
                        "user_id":         payload["user_id"],
                        "session_id":      payload["session_id"],
                        "a_id":            assessment_neo4j_id,
                        "instrument":      payload["instrument"],
                        "score":           int(payload["score"]),
                        "severity_label":  payload["severity_label"],
                        "delta":           payload["delta_from_prev"],
                        "q9_score":        int(result.item_scores[8]) if len(result.item_scores) >= 9 else 0,
                        "item_responses":  json.dumps(payload["item_responses"]),
                        "administered_at": administered_iso,
                    },
                ),
                timeout=timeout_seconds,
            )
            logger.debug(
                "Assessment Neo4j node written (user=%s session=%s score=%s)",
                payload["user_id"], payload["session_id"], payload["score"],
            )
        except Exception as exc:
            # Neo4j write failure is non-fatal: Postgres already committed,
            # so the assessment is persisted for analytics. The Neo4j node
            # can be backfilled later via the seeder or a migration job.
            logger.error(
                "Assessment Neo4j write failed (user=%s session=%s): %s "
                "— Postgres write succeeded, Neo4j node missing",
                payload["user_id"], payload["session_id"], exc,
            )

    async def schedule_retry(
        self,
        *,
        user_id: str,
        days: int,
        reason: str,
    ) -> AssessmentRetrySchedule:
        """Upsert the retry schedule for a user."""
        next_attempt = datetime.now(timezone.utc) + timedelta(days=days)
        sql = (
            "INSERT INTO assessment_retries (user_id, next_attempt_at, reason) "
            "VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "  next_attempt_at = EXCLUDED.next_attempt_at, "
            "  reason = EXCLUDED.reason"
        )
        async with self._pg.acquire() as conn:
            await conn.execute(sql, user_id, next_attempt, reason)
        return AssessmentRetrySchedule(
            user_id=user_id,
            next_attempt_at=next_attempt,
            reason=reason,
        )

    async def clear_retry(self, user_id: str) -> None:
        """Drop any pending retry, called after a successful offer."""
        sql = "DELETE FROM assessment_retries WHERE user_id = $1"
        async with self._pg.acquire() as conn:
            await conn.execute(sql, user_id)

    # PHQ-9 in-flight progress (server-authoritative score store).

    async def save_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
        state: Mapping[str, Any],
    ) -> None:
        """
        UPSERT the in-flight PHQ-9 state for ``(user_id, session_id)``.

        Called after every PHQ-9 turn that mutates phase / responses /
        active_item. The row is the authoritative source for partial
        scores until the finalize node clears it. Persisting here means
        the run survives stateless invocations, request retries, and
        callers that forget to round-trip ``phq9_state``.

        Parameters
        ----------
        user_id, session_id:
            Composite primary key.
        state:
            Mapping with PHQ-9 state keys: phase, active_item,
            responses, back_count, tier, language, user_initiated.
            Extra keys are ignored.
        """
        import json

        responses = state.get("responses") or {}
        sql = """
            INSERT INTO phq9_progress
                (user_id, session_id, phase, active_item, responses,
                 back_count, tier, language, user_initiated,
                 started_at, updated_at)
            VALUES
                ($1::uuid, $2::uuid, $3, $4, $5::jsonb,
                 $6, $7, $8, $9,
                 NOW(), NOW())
            ON CONFLICT (user_id, session_id) DO UPDATE SET
                phase          = EXCLUDED.phase,
                active_item    = EXCLUDED.active_item,
                responses      = EXCLUDED.responses,
                back_count     = EXCLUDED.back_count,
                tier           = EXCLUDED.tier,
                language       = EXCLUDED.language,
                user_initiated = EXCLUDED.user_initiated,
                updated_at     = NOW()
        """
        async with self._pg.acquire() as conn:
            await conn.execute(
                sql,
                user_id,
                session_id,
                str(state.get("phase") or "offered"),
                state.get("active_item"),
                json.dumps(responses),
                int(state.get("back_count") or 0),
                state.get("tier"),
                state.get("language"),
                bool(state.get("user_initiated") or False),
            )

    async def load_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        """
        Read the in-flight PHQ-9 state for ``(user_id, session_id)``.

        Returns a partial PHQ9SessionState dict (only the persisted
        fields), or ``None`` when no row exists. Callers merge the
        result over an ``empty_phq9_state()`` baseline so transient
        fields keep sane defaults.
        """
        import json

        sql = """
            SELECT phase, active_item, responses, back_count,
                   tier, language, user_initiated
            FROM phq9_progress
            WHERE user_id = $1::uuid AND session_id = $2::uuid
            LIMIT 1
        """
        async with self._pg.acquire() as conn:
            row = await conn.fetchrow(sql, user_id, session_id)
        if row is None:
            return None

        raw_responses = row["responses"]
        if isinstance(raw_responses, str):
            try:
                parsed_responses = json.loads(raw_responses)
            except json.JSONDecodeError:
                parsed_responses = {}
        else:
            parsed_responses = dict(raw_responses or {})

        # Cast item_id keys back to int (JSONB stores them as str).
        parsed_responses = {
            int(k): v for k, v in parsed_responses.items()
        }

        return {
            "phase": row["phase"],
            "active_item": row["active_item"],
            "responses": parsed_responses,
            "back_count": int(row["back_count"] or 0),
            "tier": row["tier"],
            "language": row["language"],
            "user_initiated": bool(row["user_initiated"]),
        }

    async def clear_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> None:
        """Drop the in-flight row after finalize or decline."""
        sql = """
            DELETE FROM phq9_progress
            WHERE user_id = $1::uuid AND session_id = $2::uuid
        """
        async with self._pg.acquire() as conn:
            await conn.execute(sql, user_id, session_id)



def days_since(then: datetime) -> int:
    """Whole days between ``then`` and now in UTC."""
    delta = datetime.now(timezone.utc) - _ensure_utc(then)
    return int(delta.total_seconds() // 86_400)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _unpack_item_scores(
    raw: Mapping[str, Any] | str | None,
) -> tuple[int, ...]:
    """Decode the ``item_responses`` JSON column into an ordered tuple."""
    import json

    if raw is None:
        return tuple([0] * NUM_ITEMS)
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return tuple([0] * NUM_ITEMS)
    else:
        data = dict(raw)
    out: list[int] = []
    for i in range(1, NUM_ITEMS + 1):
        try:
            out.append(int(data.get(str(i), 0)))
        except (TypeError, ValueError):
            out.append(0)
    return tuple(out)


def _to_json(payload: Mapping[str, Any]) -> str:
    import json

    return json.dumps(payload, default=str)


__all__ = [
    "LastPHQ9Snapshot",
    "DistressSnapshot",
    "AssessmentRetrySchedule",
    "AssessmentRepository",
    "days_since",
    "HIGH_DISTRESS_VALENCE_THRESHOLD",
    "ACUTE_DISTRESS_VALENCE_THRESHOLD",
    "ACUTE_DISTRESS_INTENSITY_THRESHOLD",
    "WORSENING_DELTA_THRESHOLD",
    "LOOKBACK_DAYS_FOR_KG",
]
