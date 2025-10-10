"""Application orchestration for programmatic access.

This module centralizes startup/shutdown of the calendar assistant so it can
be reused by different front-ends (CLI, HTTP API, etc.).
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

from config.config import AppConfig, load_config
from src.ai.gemini_agent import AgentResponse, GeminiAgent
from src.calendar_mcp.mcp_client import MCPClient
from src.reminders.reminder_service import ReminderService
from src.utils.logger import log_error, log_info


@dataclass
class NotificationRecord:
    """Container for captured reminder notifications."""

    message: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


class AssistantApp:
    """Coordinates core services for the calendar assistant."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path
        self._config: Optional[AppConfig] = None
        self._mcp_client: Optional[MCPClient] = None
        self._reminder_service: Optional[ReminderService] = None
        self._agent: Optional[GeminiAgent] = None

        self._startup_lock = asyncio.Lock()
        self._is_started = False

        # Notification handling
        self._notification_queue: asyncio.Queue[NotificationRecord] = asyncio.Queue(maxsize=100)
        self._notification_history: Deque[NotificationRecord] = deque(maxlen=100)
        self._external_notification_callback: Optional[Callable[[str], None]] = None

    @property
    def config(self) -> AppConfig:
        if not self._config:
            raise RuntimeError("AssistantApp not started yet; config unavailable")
        return self._config

    @property
    def agent(self) -> GeminiAgent:
        if not self._agent:
            raise RuntimeError("AssistantApp not started yet; agent unavailable")
        return self._agent

    @property
    def reminder_service(self) -> ReminderService:
        if not self._reminder_service:
            raise RuntimeError("AssistantApp not started yet; reminder service unavailable")
        return self._reminder_service

    @property
    def is_started(self) -> bool:
        return self._is_started

    async def startup(self) -> None:
        """Load configuration and initialize dependencies."""

        async with self._startup_lock:
            if self._is_started:
                return

            log_info("AssistantApp startup: loading configuration")
            self._config = load_config(self._config_path)

            log_info("AssistantApp startup: connecting MCP client")
            self._mcp_client = MCPClient(
                mcp_server_path=self._config.google.calendar_mcp_path,
                oauth_credentials_path=self._config.google.oauth_credentials_path,
            )
            await self._mcp_client.connect()

            log_info("AssistantApp startup: starting reminder service")
            self._reminder_service = ReminderService(
                mcp_client=self._mcp_client,
                config=self._config.reminders,
            )
            self._reminder_service.set_terminal_callback(self._handle_notification)
            await self._reminder_service.start()

            log_info("AssistantApp startup: initializing Gemini agent")
            self._agent = GeminiAgent(
                api_key=self._config.google.gemini_api_key,
                mcp_client=self._mcp_client,
                model_name=self._config.conversation.model,
                reminder_service=self._reminder_service,
            )

            self._is_started = True
            log_info("AssistantApp startup complete")

    async def shutdown(self) -> None:
        """Gracefully shut down services."""

        if not self._is_started:
            return

        log_info("AssistantApp shutdown: stopping services")

        if self._reminder_service:
            try:
                await self._reminder_service.stop()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                log_error(f"Error stopping ReminderService: {exc}")

        if self._mcp_client:
            try:
                await self._mcp_client.disconnect()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                log_error(f"Error disconnecting MCP client: {exc}")

        self._is_started = False
        log_info("AssistantApp shutdown complete")

    async def process_message(self, message: str) -> AgentResponse:
        """Send a message to the assistant and return the response."""

        if not self._is_started:
            await self.startup()

        return await self.agent.process_message(message)

    def clear_conversation(self) -> None:
        """Clear the conversation memory."""

        if not self._agent:
            raise RuntimeError("AssistantApp not started yet; cannot clear conversation")

        self._agent.clear_conversation()

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Return current conversation statistics."""

        if not self._agent:
            raise RuntimeError("AssistantApp not started yet; stats unavailable")

        return self._agent.get_conversation_stats()

    def get_reminder_stats(self) -> Dict[str, Any]:
        """Return reminder service status information."""

        if not self._reminder_service:
            raise RuntimeError("AssistantApp not started yet; stats unavailable")

        return self._reminder_service.get_stats()

    async def get_notifications(self, *, limit: int = 20, flush: bool = True) -> List[Dict[str, Any]]:
        """Retrieve reminder notifications captured so far.

        Args:
            limit: Maximum number of notifications to return
            flush: If True, consume pending notifications; otherwise return recent history
        """

        if flush:
            notifications: List[Dict[str, Any]] = []
            for _ in range(limit):
                try:
                    record = self._notification_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                notifications.append(record.to_dict())

            if notifications:
                return notifications

        # Fallback to history snapshot
        history_sample = list(self._notification_history)[:limit]
        return [record.to_dict() for record in history_sample]

    def register_notification_callback(self, callback: Callable[[str], None]) -> None:
        """Register an additional callback for real-time notifications."""

        self._external_notification_callback = callback

    def snapshot(self) -> Dict[str, Any]:
        """Return a health snapshot of the assistant state."""

        return {
            "is_started": self._is_started,
            "config_loaded": self._config is not None,
            "conversation_stats": self._agent.get_conversation_stats() if self._agent else None,
            "reminder_stats": self._reminder_service.get_stats() if self._reminder_service else None,
        }

    def _handle_notification(self, message: str) -> None:
        """Capture notifications emitted by the reminder service."""

        record = NotificationRecord(
            message=message,
            created_at=datetime.now(timezone.utc),
        )

        self._notification_history.appendleft(record)

        try:
            self._notification_queue.put_nowait(record)
        except asyncio.QueueFull:
            # Drop the oldest pending item to make room and retry
            try:
                _ = self._notification_queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            else:
                self._notification_queue.put_nowait(record)

        if self._external_notification_callback:
            try:
                self._external_notification_callback(message)
            except Exception as exc:  # pragma: no cover - callback should not break flow
                log_error(f"External notification callback failed: {exc}")

