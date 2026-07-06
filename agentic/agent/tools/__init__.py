"""Public registry for response generator tools."""

from agentic.agent.tools.context_awareness_tool import (
    calculate_math,
    current_context,
    resolve_relative_time,
    web_search,
)


# Stable name -> tool mapping. Used by response_generator to look up
# the callable when the LLM emits a tool_call with a given name.
TOOL_REGISTRY: dict = {
    "current_context": current_context,
    "web_search": web_search,
    "resolve_relative_time": resolve_relative_time,
    "calculate_math": calculate_math,
}


# Default toolset bound to the conversational response_generator.
# Crisis content tools (e.g. anything that could expose blocked
# resources) MUST NOT appear here.
_DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "current_context",
    "resolve_relative_time",
    "calculate_math",
    "web_search",
)


def get_default_toolset() -> list:
    """Return the list of tool callables for the default chat path."""
    return [TOOL_REGISTRY[name] for name in _DEFAULT_TOOL_NAMES]


def lookup(name: str):
    """Return the tool callable for ``name`` or raise KeyError."""
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
