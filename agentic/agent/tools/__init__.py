"""ambil data"""

from agentic.agent.tools.context_awareness_tool import (
    calculate_math,
    current_context,
    resolve_relative_time,
    web_search,
)


# stabil -> map.
TOOL_REGISTRY: dict = {
    "current_context": current_context,
    "web_search": web_search,
    "resolve_relative_time": resolve_relative_time,
    "calculate_math": calculate_math,
}


# skip crisis tools
_DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "current_context",
    "resolve_relative_time",
    "calculate_math",
    "web_search",
)


def get_default_toolset() -> list:
    """ret 'tool callables"""
    return [TOOL_REGISTRY[name] for name in _DEFAULT_TOOL_NAMES]


def lookup(name: str):
    """ret 'name' or raise KeyError"""
    return TOOL_REGISTRY[name]


def list_tool_names() -> tuple[str, ...]:
    return tuple(TOOL_REGISTRY.keys())


__all__ = [
    "TOOL_REGISTRY",
    "get_default_toolset",
    "lookup",
    "list_tool_names",
    "current_context",
    "web_search",
    "resolve_relative_time",
    "calculate_math",
]
