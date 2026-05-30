"""Tests for authentication tools (login, logout, whoami)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from connectlife.api import LifeConnectAuthError

from connectlife_mcp.session import SessionError
from connectlife_mcp.tools import auth


class TestLogin:
    async def test_success(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr.create = AsyncMock(return_value="tok-123")
            result = await auth.login("alice", "secret")
        assert result == {"session_id": "tok-123", "username": "alice"}

    async def test_auth_error(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr.create = AsyncMock(side_effect=LifeConnectAuthError("bad creds"))
            result = await auth.login("alice", "secret")
        assert result == {"error": "Invalid username or password"}

    async def test_connection_error(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr.create = AsyncMock(side_effect=ConnectionError("timeout"))
            result = await auth.login("alice", "secret")
        assert result == {"error": "timeout"}

    async def test_runtime_error(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr.create = AsyncMock(side_effect=RuntimeError("too many sessions"))
            result = await auth.login("alice", "secret")
        assert result == {"error": "too many sessions"}


class TestLogout:
    async def test_success(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr._default_session_id = None
            mgr.remove = AsyncMock(return_value=True)
            result = await auth.logout("tok-123")
        assert result == {"message": "Logged out successfully"}

    async def test_not_found(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr._default_session_id = None
            mgr.remove = AsyncMock(return_value=False)
            result = await auth.logout("ghost")
        assert result == {"error": "Session not found"}

    async def test_uses_default_when_no_sid(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr._default_session_id = "__default__"
            mgr.remove = AsyncMock(return_value=True)
            result = await auth.logout("")
        mgr.remove.assert_awaited_once_with("__default__")
        assert "message" in result

    async def test_no_default_no_sid(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr._default_session_id = None
            result = await auth.logout("")
        assert result == {"error": "Session not found"}


class TestWhoami:
    async def test_success(self) -> None:
        session = MagicMock()
        session.username = "alice"
        session.session_id = "tok-123"
        session.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        session.last_used = datetime(2024, 1, 2, tzinfo=UTC)
        session.appliances = {"a": MagicMock()}

        with patch.object(auth, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=session)
            result = await auth.whoami("tok-123")

        assert result["username"] == "alice"
        assert result["session_id"] == "tok-123"
        assert result["appliance_count"] == 1
        assert "2024-01-01" in result["created_at"]

    async def test_session_error(self) -> None:
        with patch.object(auth, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(side_effect=SessionError("expired"))
            result = await auth.whoami("")
        assert result == {"error": "expired"}
