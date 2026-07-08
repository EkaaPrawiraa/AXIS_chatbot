"""fastapi router"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from agentic.gateway.model import (
    ChatTurnRequest,
    ChatTurnResponse,
    SynthesizeSpeechRequest,
    SynthesizeSpeechResponse,
    TranscribeSpeechRequest,
    TranscribeSpeechResponse,
)
from agentic.gateway.service.chat_graph import ChatGraphService


logger = logging.getLogger(__name__)



def _get_service(request: Request) -> ChatGraphService:
    """set singleton svc"""
    return request.app.state.chat_service



router = APIRouter(prefix="/chat", tags=["chat"])
voice_router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/health", include_in_schema=False)
async def chat_health() -> dict[str, str]:
    """`liveness probe`"""
    return {"status": "ok"}


@router.post(
    "/invoke",
    response_model=ChatTurnResponse,
    summary="Run one chat turn (full response)",
)
async def invoke(
    payload: ChatTurnRequest,
    request: Request,
    service: ChatGraphService = Depends(_get_service),
) -> ChatTurnResponse:
    """execute one turn, return full resp."""
    req_id = getattr(request.state, "request_id", "-")
    logger.info(
        "invoke user=%s session=%s req_id=%s",
        payload.user_id,
        payload.session_id,
        req_id,
    )
    response = await service.invoke(payload)
    logger.info(
        "invoke done user=%s session=%s safety=%s req_id=%s",
        payload.user_id,
        payload.session_id,
        response.safety_flag or "none",
        req_id,
    )
    return response


@router.post(
    "/stream",
    summary="Stream one chat turn via Server-Sent Events",
    response_class=EventSourceResponse,
    responses={
        200: {
            "description": (
                "SSE stream. Events: token (text fragment), "
                "done (ChatTurnResponse JSON), error (error string)."
            ),
            "content": {"text/event-stream": {}},
        }
    },
)
async def stream(
    payload: ChatTurnRequest,
    request: Request,
    service: ChatGraphService = Depends(_get_service),
) -> EventSourceResponse:
    """const { ChatTurnResponse } = require('langGraph'); const { done, error } = ChatTurnResponse;  done.then((response) => {   // Update state }).catch((err) => {   // Handle error });"""
    req_id = getattr(request.state, "request_id", "-")
    logger.info(
        "stream start user=%s session=%s req_id=%s",
        payload.user_id,
        payload.session_id,
        req_id,
    )

    async def generator():
        done_seen = False
        async for event in service.stream(payload):
            yield event
            if event.get("event") in ("done", "error"):
                done_seen = True
                break

        if not done_seen:
            # done, fallback.
            logger.warning(
                "stream ended without done event user=%s session=%s req_id=%s",
                payload.user_id,
                payload.session_id,
                req_id,
            )
            yield {
                "event": "error",
                "data": "Stream ended without a final response.",
            }

        logger.info(
            "stream end user=%s session=%s req_id=%s",
            payload.user_id,
            payload.session_id,
            req_id,
        )

    return EventSourceResponse(generator())


@voice_router.post(
    "/synthesize",
    response_model=SynthesizeSpeechResponse,
    summary="Synthesize speech for a message",
)
async def synthesize_speech(
    payload: SynthesizeSpeechRequest,
    request: Request,
    service: ChatGraphService = Depends(_get_service),
) -> SynthesizeSpeechResponse:
    req_id = getattr(request.state, "request_id", "-")
    logger.info(
        "voice synthesize chars=%d voice=%s req_id=%s",
        len(payload.text or ""),
        payload.voice_id or "default",
        req_id,
    )
    return await service.synthesize_speech(payload)


@voice_router.post(
    "/transcribe",
    response_model=TranscribeSpeechResponse,
    summary="Transcribe one audio clip without running a full chat turn",
)
async def transcribe_speech(
    payload: TranscribeSpeechRequest,
    request: Request,
    service: ChatGraphService = Depends(_get_service),
) -> TranscribeSpeechResponse:
    req_id = getattr(request.state, "request_id", "-")
    logger.info("voice transcribe req_id=%s", req_id)
    return await service.transcribe_speech(payload)


# keep compat


def register_chat_routes(app) -> None:
    """chat router"""
    app.include_router(router)
    app.include_router(voice_router)
