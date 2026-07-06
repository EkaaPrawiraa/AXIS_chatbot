"""FastAPI dependency providers for the agentic server."""

from __future__ import annotations

from fastapi import Request

from agentic.gateway.service.chat_graph import ChatGraphService


def get_chat_service(request: Request) -> ChatGraphService:
    """
    Return the singleton ``ChatGraphService`` attached to the app state.

    The service is initialized once during the ASGI lifespan in
    ``agentic.gateway.app.lifespan``. If it is not present (e.g. in a
    test that did not run the lifespan), this raises ``AttributeError``
    which FastAPI surfaces as a 500. In tests, override via::

        app.dependency_overrides[get_chat_service] = lambda: fake_service
    """
    return request.app.state.chat_service
