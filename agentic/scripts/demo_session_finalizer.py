"""dlz"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# set env
ROOT = Path(__file__).resolve().parents[2]

def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value

_load_env(ROOT / ".env")
_load_env(ROOT / "agentic" / ".env")

USER_ID = "6aca3b8b-ddcf-4428-824e-997f921d28d3"
MAX_SESSIONS = 5  # fetch at most 5 most recent sessions


def _json_default(v: Any) -> str:
    iso = getattr(v, "isoformat", None)
    if callable(iso):
        return iso()
    return str(v)


async def fetch_sessions(pool: Any, user_id: str) -> list[dict]:
    """ambil data"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                cs.id::text   AS session_id,
                cs.channel,
                cs.status,
                cs.turn_count,
                cs.started_at,
                cs.ended_at,
                cs.sentiment_avg,
                cs.safety_escalated,
                cs.kg_processed
            FROM chat_sessions cs
            WHERE cs.user_id = $1::uuid
            ORDER BY cs.started_at DESC
            LIMIT $2
            """,
            user_id,
            MAX_SESSIONS,
        )
    return [dict(r) for r in rows]


async def fetch_messages(pool: Any, session_id: str) -> list[dict]:
    """getmsgs"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id::text AS id,
                role,
                content,
                turn_index,
                emotion_label,
                safety_flag,
                created_at
            FROM messages
            WHERE session_id = $1::uuid
            ORDER BY turn_index ASC
            """,
            session_id,
        )
    return [dict(r) for r in rows]


async def main() -> None:
    from agentic.memory.pg_vector.client import get_pool, close_pool

    pool = await get_pool()
    if pool is None:
        print("❌ Cannot connect to Postgres. Check PG_* env vars.")
        sys.exit(1)

    # ambil data
    sessions = await fetch_sessions(pool, USER_ID)
    if not sessions:
        print(f"❌ No sessions found for user {USER_ID}")
        await close_pool()
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"  USER: {USER_ID}")
    print(f"  Sessions found: {len(sessions)}")
    print(f"{'='*80}\n")

    for i, s in enumerate(sessions):
        print(f"  [{i}] session_id={s['session_id']}  channel={s['channel']}  "
              f"turns={s['turn_count']}  status={s['status']}  "
              f"kg_processed={s['kg_processed']}")
    print()

    # ngambil pesan
    all_session_messages: dict[str, list[dict]] = {}
    for s in sessions:
        sid = s["session_id"]
        msgs = await fetch_messages(pool, sid)
        all_session_messages[sid] = msgs
        user_msgs = [m for m in msgs if m["role"] == "user"]
        asst_msgs = [m for m in msgs if m["role"] == "assistant"]
        print(f"  Session {sid[:8]}… → {len(msgs)} messages "
              f"({len(user_msgs)} user, {len(asst_msgs)} assistant)")

    print(f"\n{'─'*80}")
    print("  SAMPLE CONVERSATION (first session with messages):")
    print(f"{'─'*80}\n")

    # get first sess wth msgs
    demo_session_id = None
    demo_messages = []
    for s in sessions:
        sid = s["session_id"]
        if all_session_messages[sid]:
            demo_session_id = sid
            demo_messages = all_session_messages[sid]
            break

    if not demo_session_id:
        print("❌ No messages found in any session.")
        await close_pool()
        sys.exit(1)

    for msg in demo_messages:
        role_label = "🧑 User" if msg["role"] == "user" else "🤖 Axis"
        content_preview = (msg["content"] or "")[:200]
        if len(msg["content"] or "") > 200:
            content_preview += "…"
        print(f"  [{msg['turn_index']:>3}] {role_label}: {content_preview}")
    print()

    # ngambil kg
    print(f"\n{'='*80}")
    print("  RUNNING KG EXTRACTOR (same prompt as session finalizer)")
    print(f"{'='*80}\n")

    from agentic.agent.session.finalizer_factory import make_kg_extractor, make_summarizer
    from collections import deque

    extractor = make_kg_extractor()
    summarizer = make_summarizer()
    _CONTEXT_WINDOW_MSGS = 6

    # summarize  transcript
    transcript_parts = []
    for msg in demo_messages:
        role = msg.get("role", "other")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        label = role.title()
        transcript_parts.append(f"{label}: {content}")
    transcript = "\n".join(transcript_parts)

    # summarizer.run()
    print("  ⏳ Running session summarizer...")
    try:
        summary = await summarizer(transcript=transcript, language="id")
        print(f"\n  📝 SESSION SUMMARY:\n")
        print(f"    {summary}\n")
    except Exception as exc:
        print(f"  ❌ Summarizer failed: {exc}")
        summary = ""

    # run kg extractor on each user msg w sliding win
    print(f"\n{'─'*80}")
    print("  ⏳ Running KG extractor per user message...")
    print(f"{'─'*80}\n")

    context_window: deque[dict[str, str]] = deque(maxlen=_CONTEXT_WINDOW_MSGS)
    all_extracted: list[dict[str, Any]] = []

    for msg in demo_messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()

        if role == "assistant":
            context_window.append({"role": "assistant", "content": content})
            continue

        if role != "user" or not content:
            continue

        prior = list(context_window)
        try:
            fact = await extractor(
                message=content,
                user_id=USER_ID,
                session_id=demo_session_id,
                language="id",
                preceding_context=prior or None,
            )
        except Exception as exc:
            print(f"    ❌ Extractor failed for turn {msg['turn_index']}: {exc}")
            context_window.append({"role": "user", "content": content})
            continue

        context_window.append({"role": "user", "content": content})

        if fact:
            fact_dict = dict(fact)
            fact_dict["__source_turn_index"] = msg["turn_index"]
            fact_dict["__source_content"] = content[:150]
            all_extracted.append(fact_dict)

            print(f"  ✅ Turn {msg['turn_index']}: extracted {_count_items(fact_dict)} items")
            print(f"     User said: \"{content[:100]}{'…' if len(content)>100 else ''}\"")
            _print_fact_summary(fact_dict)
            print()
        else:
            print(f"  ⊘  Turn {msg['turn_index']}: no extractable facts (trivial/phatic)")

    # show kg full
    print(f"\n{'='*80}")
    print("  AGGREGATED KNOWLEDGE GRAPH EXTRACTION RESULTS")
    print(f"{'='*80}\n")

    agg = _aggregate_facts(all_extracted)
    print(json.dumps(agg, ensure_ascii=False, indent=2, default=_json_default))

    # skip it
    print(f"\n{'='*80}")
    print("  KNOWLEDGE GRAPH vs VECTOR-ONLY COMPARISON")
    print(f"{'='*80}\n")

    _print_comparison(agg, summary, all_extracted)

    await close_pool()


def _count_items(fact: dict) -> int:
    count = 0
    for key in ("thoughts", "emotions", "experiences", "triggers",
                "behaviors", "subjects", "topics"):
        items = fact.get(key)
        if isinstance(items, list):
            count += len(items)
    relations = fact.get("relations")
    if isinstance(relations, dict):
        count += sum(len(v) for v in relations.values() if isinstance(v, list))
    return count


def _print_fact_summary(fact: dict) -> None:
    """print(facts)"""
    for key in ("thoughts", "emotions", "experiences", "triggers",
                "behaviors", "subjects", "topics"):
        items = fact.get(key)
        if not items:
            continue
        for item in items:
            if key == "thoughts":
                print(f"     💭 Thought: \"{item.get('content', '?')}\" "
                      f"(distortion={item.get('distortion', 'none')}, "
                      f"believability={item.get('believability', '?')})")
            elif key == "emotions":
                print(f"     😢 Emotion: {item.get('label', '?')} "
                      f"(intensity={item.get('intensity', '?')}, "
                      f"valence={item.get('valence', '?')})")
            elif key == "experiences":
                print(f"     📌 Experience: \"{item.get('description', '?')}\" "
                      f"(significance={item.get('significance', '?')})")
            elif key == "triggers":
                print(f"     ⚡ Trigger: \"{item.get('description', '?')}\" "
                      f"({item.get('category', '?')})")
            elif key == "behaviors":
                print(f"     🔄 Behavior: \"{item.get('description', '?')}\" "
                      f"(adaptive={item.get('adaptive', '?')})")
            elif key == "subjects":
                print(f"     👤 Subject: {item.get('name', '?')} "
                      f"({item.get('role', '?')}, "
                      f"sentiment={item.get('sentiment', '?')})")
            elif key == "topics":
                print(f"     🏷️  Topic: {item.get('name', '?')} "
                      f"({item.get('category', '?')})")

    relations = fact.get("relations")
    if isinstance(relations, dict):
        total_rels = sum(len(v) for v in relations.values() if isinstance(v, list))
        if total_rels > 0:
            print(f"     🔗 Relations: {total_rels} edges wired")
            for rel_type, pairs in relations.items():
                if isinstance(pairs, list) and pairs:
                    print(f"        - {rel_type}: {pairs}")


def _aggregate_facts(all_extracted: list[dict]) -> dict:
    """summarize facts"""
    agg: dict[str, Any] = {
        "total_extractions": len(all_extracted),
        "node_counts": {},
        "all_thoughts": [],
        "all_emotions": [],
        "all_experiences": [],
        "all_triggers": [],
        "all_behaviors": [],
        "all_subjects": [],
        "all_topics": [],
        "total_relations": 0,
        "relation_types": {},
    }

    for fact in all_extracted:
        for key, agg_key in [
            ("thoughts", "all_thoughts"),
            ("emotions", "all_emotions"),
            ("experiences", "all_experiences"),
            ("triggers", "all_triggers"),
            ("behaviors", "all_behaviors"),
            ("subjects", "all_subjects"),
            ("topics", "all_topics"),
        ]:
            items = fact.get(key)
            if isinstance(items, list):
                agg[agg_key].extend(items)

        relations = fact.get("relations")
        if isinstance(relations, dict):
            for rel_type, pairs in relations.items():
                if isinstance(pairs, list):
                    count = len(pairs)
                    agg["total_relations"] += count
                    agg["relation_types"][rel_type] = (
                        agg["relation_types"].get(rel_type, 0) + count
                    )

    for key in ("all_thoughts", "all_emotions", "all_experiences",
                "all_triggers", "all_behaviors", "all_subjects", "all_topics"):
        label = key.replace("all_", "")
        agg["node_counts"][label] = len(agg[key])

    return agg


def _print_comparison(agg: dict, summary: str, all_extracted: list[dict]) -> None:
    """print kg vs. vec"""

    print("  ┌─────────────────────────────────────────────────────────────────┐")
    print("  │              VECTOR/SEMANTIC SEARCH ONLY                        │")
    print("  ├─────────────────────────────────────────────────────────────────┤")
    print("  │ What you get:                                                   │")
    print("  │  • Session summary embedded as a single flat vector             │")
    print("  │  • Similarity search returns \"similar\" chunks                    │")
    print("  │  • NO structured relationships between entities                 │")
    print("  │  • NO causal chains (experience → emotion → thought → behavior) │")
    print("  │  • NO lifecycle tracking (supersede/deactivate/reappraise)      │")
    print("  │  • NO cross-session entity deduplication                        │")
    print("  │  • Query: \"apa trigger saya?\" → fuzzy text match only           │")
    print("  └─────────────────────────────────────────────────────────────────┘")
    print()
    print("  ┌─────────────────────────────────────────────────────────────────┐")
    print("  │              KNOWLEDGE GRAPH (our architecture)                 │")
    print("  ├─────────────────────────────────────────────────────────────────┤")

    nc = agg.get("node_counts", {})
    print(f"  │ Extracted Nodes:                                                │")
    print(f"  │  • {nc.get('thoughts', 0)} Thoughts (with CBT distortion labels)            │")
    print(f"  │  • {nc.get('emotions', 0)} Emotions (with intensity + valence)               │")
    print(f"  │  • {nc.get('experiences', 0)} Experiences (with significance scores)           │")
    print(f"  │  • {nc.get('triggers', 0)} Triggers (categorized)                            │")
    print(f"  │  • {nc.get('behaviors', 0)} Behaviors (adaptive/maladaptive tagged)           │")
    print(f"  │  • {nc.get('subjects', 0)} Subjects (people/pets/places with sentiment)      │")
    print(f"  │  • {nc.get('topics', 0)} Topics (recurring themes)                          │")
    print(f"  │                                                                 │")
    print(f"  │ Structured Relations: {agg.get('total_relations', 0)} edges                          │")
    for rtype, count in (agg.get("relation_types") or {}).items():
        print(f"  │  • {rtype}: {count}                          │")
    print(f"  │                                                                 │")
    print(f"  │ Capabilities ONLY possible with KG:                             │")
    print(f"  │  • Traverse: Experience → triggered Emotion → activated Thought │")
    print(f"  │  • Track cognitive distortion patterns across sessions           │")
    print(f"  │  • Supersede outdated thoughts when user reframes               │")
    print(f"  │  • Deactivate resolved triggers                                 │")
    print(f"  │  • Replace maladaptive behaviors with adaptive ones              │")
    print(f"  │  • Cross-session entity dedup (same \"ibu\" across sessions)       │")
    print(f"  │  • Query: \"apa distorsi kognitif yang paling sering?\" → exact    │")
    print(f"  └─────────────────────────────────────────────────────────────────┘")
    print()

    # ngelapkan
    if agg.get("all_thoughts"):
        print("  🔍 EXAMPLE: Cognitive Distortion Tracking (KG-only capability)")
        print("  ─────────────────────────────────────────────────────────────")
        for t in agg["all_thoughts"][:3]:
            print(f"     \"{t.get('content', '?')}\"")
            print(f"     → distortion: {t.get('distortion', 'none')}, "
                  f"believability: {t.get('believability', '?')}")
            print(f"     → type: {t.get('thought_type', '?')}")
            if t.get("supersedes_thought_id"):
                print(f"     → SUPERSEDES old thought: {t['supersedes_thought_id']}")
            print()

    if agg.get("all_experiences") and agg.get("all_emotions"):
        print("  🔍 EXAMPLE: Causal Chain Traversal (KG-only capability)")
        print("  ─────────────────────────────────────────────────────────────")
        print(f"     Experience: \"{agg['all_experiences'][0].get('description', '?')}\"")
        print(f"         ↓ TRIGGERED_EMOTION")
        if agg["all_emotions"]:
            print(f"     Emotion: {agg['all_emotions'][0].get('label', '?')} "
                  f"(intensity: {agg['all_emotions'][0].get('intensity', '?')})")
        if agg.get("all_thoughts"):
            print(f"         ↓ ACTIVATED_THOUGHT")
            print(f"     Thought: \"{agg['all_thoughts'][0].get('content', '?')}\"")
        if agg.get("all_behaviors"):
            print(f"         ↓ LED_TO_BEHAVIOR")
            print(f"     Behavior: \"{agg['all_behaviors'][0].get('description', '?')}\"")
        print()

    print("  ═══════════════════════════════════════════════════════════════")
    print("  CONCLUSION: The Knowledge Graph provides STRUCTURED, RELATIONAL,")
    print("  and LIFECYCLE-AWARE memory that a flat vector store cannot offer.")
    print("  Vector search finds \"similar\" text; KG understands MEANING and")
    print("  CONNECTIONS between psychological entities across sessions.")
    print("  ═══════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
