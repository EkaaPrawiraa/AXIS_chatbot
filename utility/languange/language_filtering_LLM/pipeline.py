"""Pipeline to filter slang + mental-health relevant terms."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from utility.languange.language_filtering_LLM.config import DEFAULT_CONFIG, OUT_DIR, RAW_DIR, FilterConfig
from utility.languange.language_filtering_LLM.filter_rules import compute_score, is_stopword
from utility.languange.language_filtering_LLM.io_utils import read_jsonl, write_jsonl
from utility.languange.language_scrapping.schema import REQUIRED_FIELDS


def load_raw_sources(raw_dir: Path) -> list[dict]:
    items: list[dict] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        items.extend(read_jsonl(path))
    # print(len(items))
    return items


def _normalize_usage(examples: Iterable[str], limit: int) -> list[str]:
    out: list[str] = []
    for ex in examples:
        ex = str(ex).strip()
        if not ex:
            continue
        out.append(ex)
        if len(out) >= limit:
            break
    return out


def _missing_required_fields(item: dict) -> list[str]:
    return [k for k in REQUIRED_FIELDS if k not in item]


def filter_entries(entries: Iterable[dict], config: FilterConfig) -> tuple[list[dict], dict]:
    best_by_term: dict[str, dict] = {}
    skipped_missing_schema = 0
    skipped_missing_schema_fields: dict[str, int] = defaultdict(int)
    for item in entries:
        missing = _missing_required_fields(item)
        if missing:
            skipped_missing_schema += 1
            for k in missing:
                skipped_missing_schema_fields[str(k)] += 1
            continue

        term = str(item.get("term", "")).strip()
        if not term:
            continue
        if len(term) < config.min_term_len or len(term) > config.max_term_len:
            continue
        if is_stopword(term):
            continue

        definition = str(item.get("definition_id", ""))
        examples = _normalize_usage(item.get("usage_examples") or [term], config.max_usage_examples)
        score = compute_score(term, definition, examples)
        if score.total < config.min_score_keep:
            continue

        enriched = dict(item)
        enriched["usage_examples"] = examples
        enriched["filter_score"] = round(score.total, 3)
        enriched["filter_score_detail"] = {
            "slang": round(score.slang_score, 3),
            "mental": round(score.mental_score, 3),
            "language": round(score.language_score, 3),
        }

        key = term.casefold()
        prev = best_by_term.get(key)
        if prev is None:
            best_by_term[key] = enriched
            continue

        prev_score = float(prev.get("filter_score") or 0.0)
        new_score = float(enriched.get("filter_score") or 0.0)
        if new_score > prev_score:
            best_by_term[key] = enriched
            continue
        if new_score < prev_score:
            continue

        # Tie-breakers: prefer validated entries, then longer definition_id.
        if bool(enriched.get("validated")) and not bool(prev.get("validated")):
            best_by_term[key] = enriched
            continue
        if len(str(enriched.get("definition_id") or "")) > len(
            str(prev.get("definition_id") or "")
        ):
            best_by_term[key] = enriched

    kept = list(best_by_term.values())
    kept.sort(key=lambda x: x.get("filter_score", 0), reverse=True)
    # print(kept)
    return kept[: config.max_keep], {
        "skipped_missing_schema": skipped_missing_schema,
        "skipped_missing_schema_fields": dict(skipped_missing_schema_fields),
    }


def build_stats(entries: list[dict]) -> dict:
    by_category = defaultdict(int)
    for item in entries:
        cat = item.get("category") or "unknown"
        by_category[str(cat)] += 1
    return {
        "total": len(entries),
        "by_category": dict(by_category),
    }


def run_pipeline(
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUT_DIR,
    config: FilterConfig = DEFAULT_CONFIG,
) -> dict:
    raw = load_raw_sources(raw_dir)
    filtered, skip_stats = filter_entries(raw, config)

    write_jsonl(out_dir / "filtered.jsonl", filtered)
    stats = build_stats(filtered)

    return {
        "filtered_count": len(filtered),
        "stats": stats,
        "skip_stats": skip_stats,
        "output": str(out_dir / "filtered.jsonl"),
    }
