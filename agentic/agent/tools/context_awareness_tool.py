"""init state"""

from __future__ import annotations

import ast
import json
import locale
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _local_now() -> datetime:
    # skip tzlocal. Use pytz or datetime directly.
    return datetime.now().astimezone()


def _safe_locale() -> tuple[str | None, str | None]:
    # skip warn
    try:
        loc = locale.getlocale()
        if isinstance(loc, tuple) and len(loc) == 2:
            return loc[0], loc[1]
    except Exception:
        pass
    return None, None


@tool("current_context")
def current_context() -> dict[str, Any]:
    """get mdata"""
    now = _local_now()
    lang, encoding = _safe_locale()
    return {
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "iso_datetime": now.isoformat(),
        "timezone": str(now.tzinfo) if now.tzinfo else None,
        "utc_offset": now.strftime("%z"),
        "locale": {"language": lang, "encoding": encoding},
        "weekday": now.strftime("%A"),
        "timestamp": now.timestamp(),
    }


@dataclass(frozen=True)
class WebSearchResult:
    title: str | None = None
    url: str | None = None
    content: str | None = None


_openai_client = None
_openai_disabled: bool = False


def _try_get_openai_client():
    """lazy-load None if unavailable."""
    global _openai_client, _openai_disabled
    if _openai_disabled:
        return None
    if _openai_client is not None:
        return _openai_client
    if not os.getenv("OPENAI_API_KEY"):
        _openai_disabled = True
        return None
    try:
        from openai import OpenAI  # type: ignore[import-not-found]

        _openai_client = OpenAI()
        return _openai_client
    except ImportError:
        _openai_disabled = True
        return None


def _as_dict(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        try:
            return dump()
        except Exception:
            return None
    to_dict = getattr(obj, "dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            return None
    return None


def _normalize_openai_web_results(payload: Any) -> list[dict[str, Any]]:
    """best-effort norm OpenAI"""
    results: list[dict[str, Any]] = []
    if payload is None:
        return results

    if isinstance(payload, list):
        items = payload
    else:
        d = _as_dict(payload) or {}
        items = d.get("results") or d.get("items") or []

    if not isinstance(items, list):
        return results

    for item in items:
        d = _as_dict(item) or (item if isinstance(item, dict) else None)
        if not isinstance(d, dict):
            continue
        results.append(
            WebSearchResult(
                title=d.get("title"),
                url=d.get("url") or d.get("link"),
                content=d.get("snippet")
                or d.get("content")
                or d.get("text")
                or d.get("description"),
            ).__dict__
        )
    return results


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """extract json"""
    if not text:
        return None

    candidate = text.strip()

    # prefer json.
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL | re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()

    try:
        loaded = json.loads(candidate)
        return loaded if isinstance(loaded, dict) else None
    except Exception:
        pass

    # fallback: parse outer obj
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        loaded = json.loads(candidate[start : end + 1])
        return loaded if isinstance(loaded, dict) else None
    except Exception:
        return None


_MD_LINK_RE = re.compile(r"\[(?P<title>[^\]]+?)\]\((?P<url>https?://[^)\s]+)\)")


def _extract_markdown_links(text: str, max_results: int) -> list[dict[str, Any]]:
    if not text:
        return []
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for match in _MD_LINK_RE.finditer(text):
        title = (match.group("title") or "").strip()
        url = (match.group("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)

        # ngambil link
        start = text.rfind("\n", 0, match.start())
        end = text.find("\n", match.end())
        line = text[(start + 1 if start != -1 else 0) : (end if end != -1 else len(text))].strip()

        results.append(
            WebSearchResult(
                title=title or None,
                url=url,
                content=line or None,
            ).__dict__
        )
        if len(results) >= max_results:
            break

    return results


_gemini_client = None
_gemini_disabled: bool = False


def _try_get_gemini_client():
    """load client"""
    global _gemini_client, _gemini_disabled
    if _gemini_disabled:
        return None
    if _gemini_client is not None:
        return _gemini_client
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        _gemini_disabled = True
        return None
    try:
        from google import genai  # type: ignore[import-not-found]

        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except ImportError:
        _gemini_disabled = True
        return None


def _normalize_gemini_grounding_chunks(grounding_metadata: Any) -> list[dict[str, Any]]:
    """normalize_gemini"""
    results: list[dict[str, Any]] = []
    chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if web is None:
            continue
        uri = getattr(web, "uri", None)
        title = getattr(web, "title", None)
        if not uri:
            continue
        results.append(WebSearchResult(title=title, url=uri, content=None).__dict__)
    return results


def _gemini_web_search(query: str, max_results: int) -> dict[str, Any]:
    """search web"""
    client = _try_get_gemini_client()
    if client is None:
        return {
            "query": query,
            "results": [],
            "error": "missing GOOGLE_API_KEY/GEMINI_API_KEY or google-genai package",
            "source": "gemini",
        }

    from google.genai import types  # type: ignore[import-not-found]

    model = (os.getenv("GEMINI_WEBSEARCH_MODEL") or os.getenv("GEMINI_MODEL_STRONG") or "gemini-2.5-flash").strip()

    try:
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as exc:
        err = f"gemini web_search failed: {exc}"
        logger.warning(err)
        return {"query": query, "results": [], "error": err, "source": "gemini", "model": model}

    answer = (getattr(response, "text", "") or "").strip()
    candidates = getattr(response, "candidates", None) or []
    grounding_metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
    normalized = _normalize_gemini_grounding_chunks(grounding_metadata)[:max_results]

    return {
        "query": query,
        "answer": answer,
        "results": normalized,
        "source": "gemini",
        "model": model,
    }


def _openai_web_search(query: str, max_results: int) -> dict[str, Any]:
    """web-search"""
    client = _try_get_openai_client()
    if client is None:
        return {
            "query": query,
            "results": [],
            "error": "missing OPENAI_API_KEY or openai package",
            "source": "openai",
        }

    model = (os.getenv("OPENAI_WEBSEARCH_MODEL") or "gpt-4o-mini-search-preview").strip()

    prompt = (
        "You are a web search tool. Use the live web. "
        "Return JSON only with this schema: "
        "{\"query\": string, \"results\": [{\"title\": string, \"url\": string, \"snippet\": string}]}. "
        f"Return at most {max_results} results."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
        )
    except Exception as exc:
        err = f"openai web_search failed: {exc}"
        logger.warning(err)
        return {
            "query": query,
            "results": [],
            "error": err,
            "source": "openai",
            "model": model,
        }

    text = (
        resp.choices[0].message.content
        if getattr(resp, "choices", None) and resp.choices[0].message
        else ""
    )

    parsed = _extract_json_from_text(text)
    normalized = _normalize_openai_web_results((parsed or {}).get("results"))
    if not normalized:
        normalized = _extract_markdown_links(text, max_results)

    return {
        "query": query,
        "results": normalized,
        "source": "openai",
        "model": model,
    }


@tool("web_search")
def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """search web, return normalized results"""
    if not query or not query.strip():
        return {"query": query, "results": [], "error": "empty query"}

    max_results = max(1, min(int(max_results), 10))

    # skip klo quota
    from agentic.config.llm_models import llm_provider

    if llm_provider() == "openai":
        primary, fallback = _openai_web_search, _gemini_web_search
    else:
        primary, fallback = _gemini_web_search, _openai_web_search

    result = primary(query, max_results)
    if result.get("error") and not result.get("results"):
        fb = fallback(query, max_results)
        if not fb.get("error") or fb.get("results"):
            return fb
        # skip
        result["fallback_error"] = fb.get("error")
    return result


_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


_TRAILING_TIME_RE = re.compile(
    r"^(?P<date>.*?)\s*(?:\bat\b\s*)?(?P<time>(?:\d{1,2}(?::\d{2})?\s*(?:am|pm))|(?:\d{1,2}:\d{2})|noon|midnight)\s*$",
    re.IGNORECASE,
)


def _parse_time_token(token: str) -> tuple[int, int] | None:
    t = (token or "").strip().lower()
    if not t:
        return None

    if t == "noon":
        return 12, 0
    if t == "midnight":
        return 0, 0

    # `jam 24x`
    m = re.fullmatch(r"(?P<h>\d{1,2}):(?P<m>\d{2})", t)
    if m:
        hour = int(m.group("h"))
        minute = int(m.group("m"))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
        return None

    # `jam`
    m = re.fullmatch(r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)", t)
    if not m:
        return None

    hour = int(m.group("h"))
    minute = int(m.group("m") or "0")
    ampm = m.group("ap")

    if not (1 <= hour <= 12 and 0 <= minute <= 59):
        return None

    if ampm == "am":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12

    return hour, minute


def _resolve_weekday(now: datetime, weekday_name: str, mode: str) -> datetime:
    target_weekday = _WEEKDAYS[weekday_name]
    current_weekday = now.weekday()
    delta = target_weekday - current_weekday

    if mode == "next" and delta <= 0:
        delta += 7
    if mode == "this" and delta < 0:
        delta += 7

    return now + timedelta(days=delta)


def _add_time(dt: datetime, value: int, unit: str) -> datetime:
    if "minute" in unit:
        return dt + timedelta(minutes=value)
    if "hour" in unit:
        return dt + timedelta(hours=value)
    if "day" in unit:
        return dt + timedelta(days=value)
    if "week" in unit:
        return dt + timedelta(weeks=value)
    if "month" in unit:
        return dt + timedelta(days=value * 30)
    return dt


def _subtract_time(dt: datetime, value: int, unit: str) -> datetime:
    if "minute" in unit:
        return dt - timedelta(minutes=value)
    if "hour" in unit:
        return dt - timedelta(hours=value)
    if "day" in unit:
        return dt - timedelta(days=value)
    if "week" in unit:
        return dt - timedelta(weeks=value)
    return dt


@tool("resolve_relative_time")
def resolve_relative_time(text: str, timezone: str | None = None) -> dict[str, Any]:
    """iso date"""
    tz = ZoneInfo(timezone) if timezone else _local_now().tzinfo
    now = datetime.now(tz) if tz else _local_now()
    normalized = (text or "").lower().strip()

    if not normalized:
        return {"input": text, "error": "empty input"}

    # allow trailing time
    time_token: str | None = None
    m_time = _TRAILING_TIME_RE.match(normalized)
    if m_time:
        candidate_date = (m_time.group("date") or "").strip()
        candidate_time = (m_time.group("time") or "").strip()
        parsed = _parse_time_token(candidate_time)
        # tokenize clean
        if parsed is not None and candidate_date:
            normalized = candidate_date
            time_token = candidate_time

    if normalized == "now":
        target = now
    elif normalized == "tomorrow":
        target = now + timedelta(days=1)
    elif normalized == "yesterday":
        target = now - timedelta(days=1)
    elif normalized == "next week":
        target = now + timedelta(weeks=1)
    elif normalized == "last week":
        target = now - timedelta(weeks=1)
    else:
        match = re.search(
            r"in\s+(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months)",
            normalized,
        )
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            target = _add_time(now, value, unit)
        else:
            match = re.search(
                r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)\s+ago",
                normalized,
            )
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                target = _subtract_time(now, value, unit)
            else:
                match = re.search(
                    r"(next|this)\s+(" + "|".join(_WEEKDAYS.keys()) + r")",
                    normalized,
                )
                if match:
                    mode = match.group(1)
                    weekday_name = match.group(2)
                    target = _resolve_weekday(now, weekday_name, mode)
                else:
                    return {
                        "input": text,
                        "error": "Unable to resolve relative time",
                    }

    if time_token is not None:
        parsed = _parse_time_token(time_token)
        if parsed is not None:
            hour, minute = parsed
            target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return {
        "input": text,
        "resolved_datetime": target.strftime("%Y-%m-%d %H:%M:%S"),
        "iso_datetime": target.isoformat(),
        "timezone": str(target.tzinfo) if target.tzinfo else None,
        "unix_timestamp": int(target.timestamp()),
    }


class _SafeMath(ast.NodeVisitor):
    _allowed_binops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    _allowed_unaryops = (ast.UAdd, ast.USub)

    def visit(self, node: ast.AST) -> Any:  # type: ignore[override]
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> float:
        return float(self.visit(node.body))

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numeric constants are allowed")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        if not isinstance(node.op, self._allowed_unaryops):
            raise ValueError("Unary operator not allowed")
        operand = float(self.visit(node.operand))
        if isinstance(node.op, ast.UAdd):
            return +operand
        return -operand

    def visit_BinOp(self, node: ast.BinOp) -> float:
        if not isinstance(node.op, self._allowed_binops):
            raise ValueError("Binary operator not allowed")
        left = float(self.visit(node.left))
        right = float(self.visit(node.right))

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError("Operator not supported")

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Expression element not allowed: {type(node).__name__}")


@tool("calculate_math")
def calculate_math(expression: str) -> dict[str, Any]:
    """safe_eval"""
    if not expression or not expression.strip():
        return {"expression": expression, "error": "empty expression"}

    try:
        tree = ast.parse(expression, mode="eval")
        result = _SafeMath().visit(tree)
        # retur int utk kejujuran
        if abs(result - round(result)) < 1e-12:
            return {"expression": expression, "result": int(round(result))}
        return {"expression": expression, "result": result}
    except Exception as exc:
        return {"expression": expression, "error": str(exc)}
