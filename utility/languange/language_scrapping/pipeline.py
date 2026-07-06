"""Pipeline to normalize, validate, and export the linguistic corpus."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from utility.languange.language_scrapping.config import DEFAULT_CONFIG, OUT_DIR, RAW_DIR
from utility.languange.language_scrapping.io_utils import read_jsonl, write_json, write_jsonl
from utility.languange.language_scrapping.normalize import normalize_term, normalize_text
from utility.languange.language_scrapping.schema import Entry, validate_entry


def load_raw_entries(raw_path: Path) -> list[dict]:
    """Load raw entries from either a directory of *.jsonl or a single jsonl file."""
    if raw_path.is_file():
        return read_jsonl(raw_path)
    if raw_path.is_dir():
        entries: list[dict] = []
        for path in sorted(raw_path.glob("*.jsonl")):
            entries.extend(read_jsonl(path))
        return entries
    raise FileNotFoundError(f"raw input path not found: {raw_path}")


def normalize_entries(raw_entries: Iterable[dict]) -> list[Entry]:
    normalized: list[Entry] = []
    for payload in raw_entries:
        payload = dict(payload)
        payload["term"] = normalize_term(str(payload.get("term", "")))
        payload["definition_id"] = normalize_text(str(payload.get("definition_id", "")))
        payload["definition_en"] = normalize_text(str(payload.get("definition_en", "")))
        examples = payload.get("usage_examples") or []
        payload["usage_examples"] = [normalize_text(str(x)) for x in examples if str(x).strip()]
        payload["clinical_note"] = normalize_text(str(payload.get("clinical_note", "")))
        payload["source"] = normalize_text(str(payload.get("source", "")))
        payload["added_date"] = normalize_text(str(payload.get("added_date", "")))
        normalized.append(Entry.from_dict(payload))
    return normalized


def dedupe_entries(entries: Iterable[Entry]) -> list[Entry]:
    by_term: dict[str, Entry] = {}
    for entry in entries:
        key = entry.term
        if key not in by_term:
            by_term[key] = entry
            continue
        # Prefer validated entries; otherwise keep the first.
        if entry.validated and not by_term[key].validated:
            by_term[key] = entry
    return list(by_term.values())


def collect_validation_errors(entries: Iterable[Entry]) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for entry in entries:
        err = validate_entry(entry)
        if err:
            errors[entry.term] = err
    return errors


def estimate_tokens(text: str, ratio: float) -> int:
    words = len([w for w in text.split(" ") if w])
    return int(words * ratio)


def entry_to_prompt_line(entry: Entry) -> str:
    return (
        f"- {entry.term}: {entry.definition_id} "
        f"(cat={entry.category}, lang={entry.language}, weight={entry.emotional_weight}, "
        f"distress={str(entry.distress_signal).lower()}, escalate={str(entry.escalation_flag).lower()})"
    )


def select_for_prompt(entries: list[Entry], config=DEFAULT_CONFIG) -> list[Entry]:
    # Prioritize L4, then L2, then L1/L3.
    buckets: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        buckets[entry.category].append(entry)

    ordered: list[Entry] = []
    ordered.extend(sorted(buckets.get("L4", []), key=lambda e: e.term))
    ordered.extend(sorted(buckets.get("L2", []), key=lambda e: e.term))
    ordered.extend(sorted(buckets.get("L1", []), key=lambda e: e.term))
    ordered.extend(sorted(buckets.get("L3", []), key=lambda e: e.term))

    selected: list[Entry] = []
    token_budget = config.max_prompt_tokens
    for entry in ordered:
        if len(selected) >= config.max_prompt_entries:
            break
        line = entry_to_prompt_line(entry)
        cost = estimate_tokens(line, config.token_estimate_ratio)
        if token_budget - cost <= 0:
            break
        selected.append(entry)
        token_budget -= cost
    return selected


def build_prompt_block(entries: list[Entry]) -> str:
    lines = ["Indonesian linguistic context (static):"]
    lines.extend(entry_to_prompt_line(e) for e in entries)
    return "\n".join(lines)


def build_stats(entries: list[Entry], validation_errors: dict[str, list[str]]) -> dict:
    by_category = defaultdict(int)
    for entry in entries:
        by_category[entry.category] += 1
    return {
        "total": len(entries),
        "by_category": dict(by_category),
        "validation_errors": validation_errors,
    }


def run_pipeline(raw_dir: Path = RAW_DIR, out_dir: Path = OUT_DIR) -> dict:
    raw_entries = load_raw_entries(raw_dir)
    normalized = normalize_entries(raw_entries)
    deduped = dedupe_entries(normalized)

    validation_errors = collect_validation_errors(deduped)
    review_queue = [e for e in deduped if not e.validated]

    selected_prompt_entries = select_for_prompt(deduped)
    prompt_block = build_prompt_block(selected_prompt_entries)

    # Outputs
    write_jsonl(out_dir / "corpus.jsonl", [e.to_dict() for e in deduped])
    write_jsonl(out_dir / "review_queue.jsonl", [e.to_dict() for e in review_queue])
    (out_dir / "prompt_snippet.txt").write_text(prompt_block, encoding="utf-8")

    stats = build_stats(deduped, validation_errors)
    write_json(out_dir / "stats.json", stats)

    return {
        "prompt_entry_count": len(selected_prompt_entries),
        "prompt_text": prompt_block,
        "stats": stats,
    }
