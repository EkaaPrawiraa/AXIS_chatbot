"""fastapi deps"""

from __future__ import annotations

from fastapi import Request

from agentic.gateway.service.chat_graph import ChatGraphService


def get_chat_service(request: Request) -> ChatGraphService:
    """satu_chat_graph_service"""
    return request.app.state.chat_service
