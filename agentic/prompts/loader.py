"""skip klo error"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml



PROMPTS_ROOT: Path = Path(__file__).resolve().parent
REQUIRED_KEYS: frozenset[str] = frozenset({"name", "system"})
ALLOWED_LAYERS: frozenset[str] = frozenset(
    {"system", "node", "assessment", "guardrail", "cbt"}
)



class PromptNotFoundError(FileNotFoundError):
    """nlf dgn dlm"""


class PromptSchemaError(ValueError):
    """yaml ngeluar"""



@dataclass(frozen=True)
class PromptBundle:
    """ambil metadata"""

    ref: str
    name: str
    system: str
    description: str | None = None
    layer: str | None = None
    language: str | None = None
    version: str | None = None
    notes: str | None = None
    tags: tuple[str, ...] = ()
    raw: Mapping[str, object] | None = None



_CACHE: dict[str, PromptBundle] = {}


def clear_cache() -> None:
    """drop cache, use hot reload."""
    _CACHE.clear()



def load_prompt(ref: str) -> str:
    """ngk kalo ngotot"""
    return load_prompt_bundle(ref).system


def load_prompt_bundle(ref: str) -> PromptBundle:
    """retire"""
    normalized = _normalize_ref(ref)
    cached = _CACHE.get(normalized)
    if cached is not None:
        return cached

    path = _resolve_path(normalized)
    bundle = _read_and_validate(normalized, path)
    _CACHE[normalized] = bundle
    return bundle


def list_prompts() -> tuple[str, ...]:
    """`get all`"""
    refs: list[str] = []
    for path in sorted(PROMPTS_ROOT.rglob("*.yaml")):
        if path.parent == PROMPTS_ROOT:
            # expose stem
            refs.append(path.stem)
            continue
        rel = path.relative_to(PROMPTS_ROOT).with_suffix("")
        refs.append(rel.as_posix())
    return tuple(refs)



def _normalize_ref(ref: str) -> str:
    if not ref:
        raise PromptNotFoundError("prompt ref is empty")
    cleaned = ref.strip().strip("/")
    if cleaned.endswith(".yaml") or cleaned.endswith(".yml"):
        cleaned = os.path.splitext(cleaned)[0]
    return cleaned


def _resolve_path(ref: str) -> Path:
    """find yaml path"""
    candidates = [
        PROMPTS_ROOT / f"{ref}.yaml",
        PROMPTS_ROOT / f"{ref}.yml",
    ]
    for cand in candidates:
        if cand.is_file():
            # skip dir
            if PROMPTS_ROOT not in cand.resolve().parents:
                raise PromptNotFoundError(
                    f"resolved path escapes prompts root: {cand}"
                )
            return cand
    raise PromptNotFoundError(
        f"no prompt file for ref={ref!r} (looked under {PROMPTS_ROOT})"
    )


def _read_and_validate(ref: str, path: Path) -> PromptBundle:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise PromptSchemaError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise PromptSchemaError(
            f"prompt {ref} root must be a mapping, got {type(data).__name__}"
        )

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise PromptSchemaError(
            f"prompt {ref} missing required keys: {sorted(missing)}"
        )

    layer = data.get("layer")
    if layer is not None and layer not in ALLOWED_LAYERS:
        raise PromptSchemaError(
            f"prompt {ref} has invalid layer={layer!r}; "
            f"allowed: {sorted(ALLOWED_LAYERS)}"
        )

    system_text = str(data["system"]).strip()
    if not system_text:
        raise PromptSchemaError(f"prompt {ref} system text is empty")

    tags_raw = data.get("tags") or []
    if not isinstance(tags_raw, (list, tuple)):
        raise PromptSchemaError(f"prompt {ref} tags must be a list")

    return PromptBundle(
        ref=ref,
        name=str(data["name"]),
        system=system_text,
        description=_opt_str(data.get("description")),
        layer=_opt_str(layer),
        language=_opt_str(data.get("language")),
        version=_opt_str(data.get("version")),
        notes=_opt_str(data.get("notes")),
        tags=tuple(str(t) for t in tags_raw),
        raw=data,
    )


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
