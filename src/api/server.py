"""HTTP API for interacting with the calendar assistant."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.app.assistant_app import AssistantApp


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")


class ChatResponse(BaseModel):
    message: str
    tools_used: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    conversation: Dict[str, Any]
    reminders: Dict[str, Any]


class NotificationBatch(BaseModel):
    notifications: List[Dict[str, Any]]


def get_assistant(app: FastAPI) -> AssistantApp:
    assistant = getattr(app.state, "assistant", None)
    if assistant is None:
        raise RuntimeError("Assistant instance is not configured on the application state")
    return assistant


def create_app(assistant_instance: AssistantApp | None = None) -> FastAPI:
    assistant = assistant_instance or AssistantApp()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.assistant = assistant
        await assistant.startup()
        try:
            yield
        finally:
            await assistant.shutdown()

    app = FastAPI(
        title="Calendar Assistant API",
        version="1.0.0",
        description="REST API for interacting with the AI-powered calendar assistant.",
        lifespan=lifespan,
    )

    @app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
    async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
        try:
            response = await get_assistant(app).process_message(payload.message)
            return ChatResponse(
                message=response.message,
                tools_used=response.tools_used,
                metadata=response.metadata,
            )
        except Exception as exc:  # pragma: no cover - surface runtime errors cleanly
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process message: {exc}",
            ) from exc

    @app.post("/conversation/clear", status_code=status.HTTP_204_NO_CONTENT)
    async def clear_conversation_endpoint() -> None:
        try:
            get_assistant(app).clear_conversation()
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clear conversation: {exc}",
            ) from exc

    @app.get("/stats", response_model=StatsResponse)
    async def stats_endpoint() -> StatsResponse:
        try:
            return StatsResponse(
                conversation=get_assistant(app).get_conversation_stats(),
                reminders=get_assistant(app).get_reminder_stats(),
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch stats: {exc}",
            ) from exc

    @app.get("/notifications", response_model=NotificationBatch)
    async def notifications_endpoint(limit: int = 20, flush: bool = True) -> NotificationBatch:
        try:
            notifications = await get_assistant(app).get_notifications(limit=limit, flush=flush)
            return NotificationBatch(notifications=notifications)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch notifications: {exc}",
            ) from exc

    @app.get("/health")
    async def health_endpoint() -> Dict[str, Any]:
        try:
            return get_assistant(app).snapshot()
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch health snapshot: {exc}",
            ) from exc

    return app


app = create_app()
