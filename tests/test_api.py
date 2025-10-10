from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from src.ai.gemini_agent import AgentResponse
from src.api.server import create_app


class FakeAssistant:
    def __init__(self) -> None:
        self.started = False
        self.cleared = False
        self.messages: List[str] = []

    async def startup(self) -> None:
        self.started = True

    async def shutdown(self) -> None:
        self.started = False

    async def process_message(self, message: str) -> AgentResponse:
        self.messages.append(message)
        return AgentResponse(message=f"echo: {message}", tools_used=["test"], metadata={"echo": True})

    def clear_conversation(self) -> None:
        self.cleared = True

    def get_conversation_stats(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.messages) * 2,
            "user_messages": len(self.messages),
            "assistant_messages": len(self.messages),
            "pending_actions": 0,
        }

    def get_reminder_stats(self) -> Dict[str, Any]:
        return {
            "is_started": self.started,
            "monitor": {
                "sent_reminders": 1,
                "custom_reminders_pending": 0,
            },
            "dispatcher": {"queue_size": 0},
        }

    async def get_notifications(self, *, limit: int = 20, flush: bool = True) -> List[Dict[str, Any]]:  # noqa: ARG002
        return [
            {
                "message": "Test notification",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]

    def snapshot(self) -> Dict[str, Any]:
        return {"is_started": self.started, "config_loaded": True}


def build_test_client() -> TestClient:
    fake_assistant = FakeAssistant()
    app = create_app(fake_assistant)
    return TestClient(app)


def test_chat_endpoint_returns_response() -> None:
    with build_test_client() as client:
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["message"] == "echo: hello"
        assert payload["tools_used"] == ["test"]
        assert payload["metadata"] == {"echo": True}


def test_clear_conversation_sets_flag() -> None:
    with build_test_client() as client:
        resp = client.post("/conversation/clear")
        assert resp.status_code == 204


def test_stats_endpoint_returns_data() -> None:
    with build_test_client() as client:
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "conversation" in data
        assert "reminders" in data


def test_notifications_endpoint_returns_batch() -> None:
    with build_test_client() as client:
        resp = client.get("/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert "notifications" in data
        assert len(data["notifications"]) == 1


def test_health_endpoint_returns_snapshot() -> None:
    with build_test_client() as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["config_loaded"] is True
