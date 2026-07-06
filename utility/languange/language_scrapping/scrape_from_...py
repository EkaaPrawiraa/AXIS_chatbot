#!/usr/bin/env python3
"""Scrape/ingest raw linguistic entries into data/raw.

This script supports local files plus Hugging Face datasets. It uses
official APIs when available; otherwise it performs lightweight HTTP
fetches. It does not scrape Twitter/X (S2 is skipped).
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utility.languange.language_scrapping.config import RAW_DIR, SOURCES_DIR
from utility.languange.language_scrapping.io_utils import ensure_dir, write_jsonl


HF_DATASET_SERVER = "https://datasets-server.huggingface.co"
HF_API = "https://huggingface.co/api/datasets"
HF_GENZ_CSV_URL = (
	"https://huggingface.co/datasets/MLBtrio/genz-slang-dataset/resolve/main/all_slangs.csv"
)


def _parse_bool(value: str) -> bool:
	return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _today_tag() -> str:
	return datetime.now().strftime("%Y-%m")


def _build_entry(
	*,
	term: str,
	definition_id: str,
	definition_en: str,
	usage_examples: list[str],
	source: str,
	category: str = "L1",
	language: str = "id",
	register: str = "slang",
	emotional_weight: str = "low",
	distress_signal: bool = False,
	escalation_flag: bool = False,
	clinical_note: str = "",
	validated: bool = False,
	added_date: str | None = None,
) -> dict:
	return {
		"term": term,
		"category": category,
		"language": language,
		"register": register,
		"definition_id": definition_id,
		"definition_en": definition_en,
		"usage_examples": usage_examples,
		"emotional_weight": emotional_weight,
		"distress_signal": distress_signal,
		"escalation_flag": escalation_flag,
		"clinical_note": clinical_note,
		"source": source,
		"validated": validated,
		"added_date": added_date or _today_tag(),
	}


def _parse_manual_line(line: str) -> dict:
	parts = [p.strip() for p in line.split("|")]
	if len(parts) != 14:
		raise ValueError(f"expected 14 fields, got {len(parts)}")

	(
		term,
		category,
		language,
		register,
		definition_id,
		definition_en,
		usage_examples,
		emotional_weight,
		distress_signal,
		escalation_flag,
		clinical_note,
		source,
		validated,
		added_date,
	) = parts

	examples = [x.strip() for x in usage_examples.split(",") if x.strip()]
	return {
		"term": term,
		"category": category,
		"language": language,
		"register": register,
		"definition_id": definition_id,
		"definition_en": definition_en,
		"usage_examples": examples,
		"emotional_weight": emotional_weight,
		"distress_signal": _parse_bool(distress_signal),
		"escalation_flag": _parse_bool(escalation_flag),
		"clinical_note": clinical_note,
		"source": source,
		"validated": _parse_bool(validated),
		"added_date": added_date or datetime.now().strftime("%Y-%m"),
	}


def ingest_manual_file(input_path: Path, output_path: Path) -> int:
	items: list[dict] = []
	with input_path.open("r", encoding="utf-8") as f:
		for raw in f:
			line = raw.strip()
			if not line or line.startswith("#"):
				continue
			items.append(_parse_manual_line(line))

	ensure_dir(output_path.parent)
	write_jsonl(output_path, items)
	return len(items)


def ingest_mapping_csv(
	*,
	input_path: Path,
	output_path: Path,
	term_key: str,
	formal_key: str,
	source_label: str,
) -> int:
	items: list[dict] = []
	with input_path.open("r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			term = (row.get(term_key) or "").strip()
			formal = (row.get(formal_key) or "").strip()
			if not term or not formal:
				continue
			items.append(
				_build_entry(
					term=term,
					definition_id=f"Padanan dari '{term}' adalah '{formal}'.",
					definition_en="Indonesian slang normalization.",
					usage_examples=[term],
					source=source_label,
				)
			)

	ensure_dir(output_path.parent)
	write_jsonl(output_path, items)
	return len(items)


def ingest_pair_csv(
	*,
	input_path: Path,
	output_path: Path,
	source_label: str,
) -> int:
	items: list[dict] = []
	with input_path.open("r", encoding="utf-8") as f:
		reader = csv.reader(f)
		for row in reader:
			if len(row) < 2:
				continue
			term = row[0].strip()
			formal = row[1].strip()
			if not term or not formal:
				continue
			items.append(
				_build_entry(
					term=term,
					definition_id=f"Padanan dari '{term}' adalah '{formal}'.",
					definition_en="Indonesian slang normalization.",
					usage_examples=[term],
					source=source_label,
				)
			)

	ensure_dir(output_path.parent)
	write_jsonl(output_path, items)
	return len(items)


def _http_get_json(url: str) -> dict:
	req = Request(url, headers={"User-Agent": "CompanionshipChatBot/1.0"})
	with urlopen(req, timeout=40) as resp:
		return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str) -> str:
	req = Request(url, headers={"User-Agent": "CompanionshipChatBot/1.0"})
	with urlopen(req, timeout=40) as resp:
		return resp.read().decode("utf-8", errors="replace")


def _fetch_hf_configs(dataset: str) -> list[str]:
	url = f"{HF_DATASET_SERVER}/configs?dataset={dataset}"
	data = _http_get_json(url)
	configs = data.get("configs") or []
	return [c.get("config") for c in configs if c.get("config")]


def _fetch_hf_repo_files(dataset: str) -> list[str]:
	url = f"{HF_API}/{dataset}"
	data = _http_get_json(url)
	files = data.get("siblings") or []
	return [f.get("rfilename") for f in files if f.get("rfilename")]


def _download_hf_file(dataset: str, filename: str) -> str:
	url = f"https://huggingface.co/datasets/{dataset}/resolve/main/{filename}"
	return _http_get_text(url)


def _parse_csv_text(text: str) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	reader = csv.DictReader(text.splitlines())
	for row in reader:
		rows.append({k: v for k, v in row.items() if k})
	return rows


def _parse_jsonl_text(text: str) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	for line in text.splitlines():
		line = line.strip()
		if not line:
			continue
		rows.append(json.loads(line))
	return rows


def _parse_json_text(text: str) -> list[dict[str, Any]]:
	data = json.loads(text)
	if isinstance(data, list):
		return data
	if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
		return data["data"]
	return []


def _extract_term_meaning(row: dict[str, Any]) -> tuple[str, str]:
	term = (
		row.get("slang")
		or row.get("term")
		or row.get("kata")
		or row.get("kata_gaul")
		or row.get("word")
		or row.get("kolokial")
		or row.get("informal")
		or ""
	).strip()
	meaning = (
		row.get("formal")
		or row.get("meaning")
		or row.get("definition")
		or row.get("padanan")
		or row.get("kata_baku")
		or row.get("standard")
		or row.get("baku")
		or ""
	).strip()

	if not term:
		for value in row.values():
			if value and str(value).strip():
				term = str(value).strip()
				break
	if not meaning:
		vals = [str(v).strip() for v in row.values() if v and str(v).strip()]
		if len(vals) >= 2:
			meaning = vals[1]

	return term, meaning


def _fetch_hf_rows(dataset: str, config: str, split: str) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	offset = 0
	page_size = 100
	while True:
		url = (
			f"{HF_DATASET_SERVER}/rows?dataset={dataset}"
			f"&config={config}&split={split}&offset={offset}&length={page_size}"
		)
		payload = _http_get_json(url)
		chunk = payload.get("rows") or []
		if not chunk:
			break
		rows.extend([r.get("row", {}) for r in chunk])
		offset += page_size
		time.sleep(0.2)
		if len(chunk) < page_size:
			break
	return rows


def ingest_hf_dataset(*, dataset: str, output_path: Path, source_label: str) -> int:
	items: list[dict] = []
	try:
		configs = _fetch_hf_configs(dataset)
	except (HTTPError, URLError):
		configs = []

	if configs:
		for config in configs:
			for split in ("train", "validation", "test"):
				try:
					rows = _fetch_hf_rows(dataset, config, split)
				except (HTTPError, URLError):
					continue
				for row in rows:
					term, meaning = _extract_term_meaning(row)
					if not term:
						continue
					if not meaning:
						meaning = "Slang term (definition pending)."
					example = row.get("example") or row.get("context") or ""
					usage = [str(example).strip()] if str(example).strip() else [term]
					items.append(
						_build_entry(
							term=term,
							definition_id=meaning,
							definition_en="Indonesian slang entry.",
							usage_examples=usage,
							source=source_label,
						)
					)
	else:
		# Fallback to Hugging Face dataset files.
		try:
			files = _fetch_hf_repo_files(dataset)
		except (HTTPError, URLError) as exc:
			print(f"Warning: failed to fetch HF repo files for {dataset}: {exc}")
			return 0

		for filename in files:
			if not filename:
				continue
			if not filename.endswith((".csv", ".jsonl", ".json")):
				continue
			try:
				text = _download_hf_file(dataset, filename)
			except (HTTPError, URLError) as exc:
				print(f"Warning: failed to download {filename} from {dataset}: {exc}")
				continue
			if filename.endswith(".csv"):
				rows = _parse_csv_text(text)
			elif filename.endswith(".jsonl"):
				rows = _parse_jsonl_text(text)
			else:
				rows = _parse_json_text(text)
			for row in rows:
				term, meaning = _extract_term_meaning(row)
				if not term:
					continue
				if not meaning:
					meaning = "Slang term (definition pending)."
				example = row.get("example") or row.get("context") or ""
				usage = [str(example).strip()] if str(example).strip() else [term]
				items.append(
					_build_entry(
						term=term,
						definition_id=meaning,
						definition_en="Indonesian slang entry.",
						usage_examples=usage,
						source=source_label,
					)
				)

	ensure_dir(output_path.parent)
	write_jsonl(output_path, items)
	return len(items)


def ingest_direct_csv_url(*, url: str, output_path: Path, source_label: str) -> int:
	text = _http_get_text(url)
	rows = _parse_csv_text(text)
	items: list[dict] = []
	for row in rows:
		term, meaning = _extract_term_meaning(row)
		if not term:
			continue
		if not meaning:
			meaning = "Slang term (definition pending)."
		example = row.get("example") or row.get("context") or ""
		usage = [str(example).strip()] if str(example).strip() else [term]
		items.append(
			_build_entry(
				term=term,
				definition_id=meaning,
				definition_en="Indonesian slang entry.",
				usage_examples=usage,
				source=source_label,
			)
		)

	ensure_dir(output_path.parent)
	write_jsonl(output_path, items)
	return len(items)


def main() -> int:
	parser = argparse.ArgumentParser(description="Ingest local linguistic sources into data/raw.")
	parser.add_argument(
		"--input",
		default=str(SOURCES_DIR / "manual_seed.txt"),
		help="Path to manual seed file (pipe-separated)",
	)
	parser.add_argument(
		"--output",
		default=str(RAW_DIR / "manual_seed.jsonl"),
		help="Output jsonl path under data/raw",
	)
	parser.add_argument(
		"--source",
		action="append",
		default=[],
		help=(
			"Source to ingest: manual, colloquial, slang_indo, hf_indonesia_slang, "
			"hf_genz_slang, or all"
		),
	)
	args = parser.parse_args()

	sources = args.source or ["manual"]
	if "all" in sources:
		sources = [
			"manual",
			"colloquial",
			"slang_indo",
			"hf_indonesia_slang",
			"hf_genz_slang",
		]

	if "manual" in sources:
		input_path = Path(args.input)
		output_path = Path(args.output)
		if not input_path.exists():
			raise SystemExit(f"input not found: {input_path}")
		count = ingest_manual_file(input_path, output_path)
		print(f"Wrote {count} entries to {output_path}")

	if "colloquial" in sources:
		input_path = SOURCES_DIR / "colloquial-indonesian-lexicon.csv"
		output_path = RAW_DIR / "colloquial-indonesian-lexicon.jsonl"
		if input_path.exists():
			count = ingest_mapping_csv(
				input_path=input_path,
				output_path=output_path,
				term_key="slang",
				formal_key="formal",
				source_label="S6: colloquial-indonesian-lexicon",
			)
			print(f"Wrote {count} entries to {output_path}")

	if "slang_indo" in sources:
		input_path = SOURCES_DIR / "slang_indo.csv.xls"
		output_path = RAW_DIR / "slang_indo.jsonl"
		if input_path.exists():
			count = ingest_pair_csv(
				input_path=input_path,
				output_path=output_path,
				source_label="S6: slang_indo",
			)
			print(f"Wrote {count} entries to {output_path}")

	if "hf_indonesia_slang" in sources:
		output_path = RAW_DIR / "hf_indonesia_slang.jsonl"
		count = ingest_hf_dataset(
			dataset="theonlydo/indonesia-slang",
			output_path=output_path,
			source_label="S6: HF theonlydo/indonesia-slang",
		)
		print(f"Wrote {count} entries to {output_path}")

	if "hf_genz_slang" in sources:
		output_path = RAW_DIR / "hf_genz_slang.jsonl"
		count = ingest_direct_csv_url(
			url=HF_GENZ_CSV_URL,
			output_path=output_path,
			source_label="S6: HF MLBtrio/genz-slang-dataset",
		)
		print(f"Wrote {count} entries to {output_path}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
