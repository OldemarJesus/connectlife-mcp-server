"""Tests for session lifecycle and SessionManager."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectlife_mcp.session import (
    SESSION_TTL_SECONDS,
    Session,
    SessionError,
    SessionManager,
)


@pytest.fixture
def fresh_manager() -> SessionManager:
    """Return a brand-new SessionManager with no default session."""
    return SessionManager()


class TestSessionManagerCreate:
    """Tests for SessionManager.create()."""

    async def test_create_success(self, fresh_manager: SessionManager) -> None:
        """Creating a session returns a non-empty token."""
        with patch.object(fresh_manager, "_authenticate", new_callable=AsyncMock) as mock_auth:
            mock_api = MagicMock()
            mock_api.appliances = []
            mock_auth.return_value = mock_api

            sid = await fresh_manager.create("u", "p")

        assert sid
        assert isinstance(sid, str)
        assert sid in fresh_manager._sessions

    async def test_create_rejects_when_max_sessions_reached(
        self, fresh_manager: SessionManager
    ) -> None:
        """Exceeding CONNECTLIFE_MAX_SESSIONS raises RuntimeError."""
        with patch.object(fresh_manager, "_authenticate", new_callable=AsyncMock) as mock_auth:
            mock_api = MagicMock()
            mock_api.appliances = []
            mock_auth.return_value = mock_api

            for i in range(100):
                await fresh_manager.create(f"u{i}", "p")

            with pytest.raises(RuntimeError, match="Maximum concurrent sessions reached"):
                await fresh_manager.create("overflow", "p")


class TestSessionManagerGet:
    """Tests for SessionManager.get()."""

    async def test_get_missing_raises(self, fresh_manager: SessionManager) -> None:
        """Getting a non-existent session raises SessionError."""
        with pytest.raises(SessionError, match="Session not found or expired"):
            fresh_manager.get("nope")

    async def test_get_expired_raises(self, fresh_manager: SessionManager) -> None:
        """An expired session raises SessionError."""
        old = datetime.now(tz=UTC) - timedelta(seconds=SESSION_TTL_SECONDS + 1)
        session = Session(
            session_id="expired",
            username="u",
            api=MagicMock(),
            last_used=old,
        )
        fresh_manager._sessions["expired"] = session
        with pytest.raises(SessionError, match="Session has expired"):
            fresh_manager.get("expired")

    async def test_get_updates_last_used(self, fresh_manager: SessionManager) -> None:
        """get() bumps last_used to now."""
        session = Session(session_id="live", username="u", api=MagicMock())
        fresh_manager._sessions["live"] = session
        before = session.last_used
        fresh_manager.get("live")
        assert session.last_used > before


class TestSessionManagerResolve:
    """Tests for SessionManager.resolve_session()."""

    async def test_resolve_explicit(self, fresh_manager: SessionManager) -> None:
        """resolve_session returns the requested explicit session."""
        session = Session(session_id="s1", username="u", api=MagicMock())
        fresh_manager._sessions["s1"] = session
        resolved = await fresh_manager.resolve_session("s1")
        assert resolved.session_id == "s1"

    async def test_resolve_no_default_raises(self, fresh_manager: SessionManager) -> None:
        """Without a default session and no id, resolve raises."""
        with pytest.raises(SessionError, match="No session provided"):
            await fresh_manager.resolve_session(None)

    async def test_resolve_default_relogin(self, fresh_manager: SessionManager) -> None:
        """Default session auto-re-authenticates when missing."""
        fresh_manager._default_session_id = "__default__"
        fresh_manager._default_credentials = ("u", "p")
        with patch.object(
            fresh_manager, "_relogin_default", new_callable=AsyncMock
        ) as mock_relogin:
            mock_relogin.return_value = Session(
                session_id="__default__",
                username="u",
                api=MagicMock(),
            )
            resolved = await fresh_manager.resolve_session(None)
        assert resolved.session_id == "__default__"


class TestSessionManagerRemove:
    """Tests for SessionManager.remove()."""

    async def test_remove_existing(self, fresh_manager: SessionManager) -> None:
        """Removing an existing session returns True."""
        session = Session(session_id="r1", username="u", api=MagicMock())
        fresh_manager._sessions["r1"] = session
        assert await fresh_manager.remove("r1") is True
        assert "r1" not in fresh_manager._sessions

    async def test_remove_missing(self, fresh_manager: SessionManager) -> None:
        """Removing a missing session returns False."""
        assert await fresh_manager.remove("ghost") is False

    async def test_remove_cancels_poll_task(self, fresh_manager: SessionManager) -> None:
        """remove() cancels an active polling task."""
        task = asyncio.create_task(asyncio.sleep(60))
        session = Session(session_id="r2", username="u", api=MagicMock(), poll_task=task)
        fresh_manager._sessions["r2"] = session
        await fresh_manager.remove("r2")
        # Give the event loop a chance to process the cancellation.
        await asyncio.sleep(0)
        assert task.cancelled()


class TestAuthenticate:
    """Tests for the internal _authenticate helper."""

    async def test_authenticate_success(self, fresh_manager: SessionManager) -> None:
        """Happy path: authenticate + login + get_appliances."""
        with patch("connectlife_mcp.session.ConnectLifeApi") as MockApi:
            api = MockApi.return_value
            api.authenticate = AsyncMock(return_value=True)
            api.login = AsyncMock()
            api.get_appliances = AsyncMock()
            result = await fresh_manager._authenticate("u", "p")
        assert result is api
        api.authenticate.assert_awaited_once()
        api.login.assert_awaited_once()
        api.get_appliances.assert_awaited_once()

    async def test_authenticate_failure(self, fresh_manager: SessionManager) -> None:
        """authenticate() returning False raises LifeConnectAuthError."""
        with patch("connectlife_mcp.session.ConnectLifeApi") as MockApi:
            api = MockApi.return_value
            api.authenticate = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="Authentication failed"):
                await fresh_manager._authenticate("u", "p")

    async def test_authenticate_api_error(self, fresh_manager: SessionManager) -> None:
        """ConnectLife API errors are wrapped in ConnectionError."""
        from connectlife.api import LifeConnectError

        with patch("connectlife_mcp.session.ConnectLifeApi") as MockApi:
            api = MockApi.return_value
            api.authenticate = AsyncMock(side_effect=LifeConnectError("boom"))
            with pytest.raises(ConnectionError, match="ConnectLife API error"):
                await fresh_manager._authenticate("u", "p")


class TestEvictExpired:
    """Tests for _evict_expired_locked."""

    async def test_eviction_removes_stale_sessions(self, fresh_manager: SessionManager) -> None:
        """Expired sessions are removed and their tasks cancelled."""
        old = datetime.now(tz=UTC) - timedelta(seconds=SESSION_TTL_SECONDS + 10)
        task = asyncio.create_task(asyncio.sleep(60))
        session = Session(
            session_id="old", username="u", api=MagicMock(), last_used=old, poll_task=task
        )
        fresh_manager._sessions["old"] = session
        fresh_manager._evict_expired_locked()
        assert "old" not in fresh_manager._sessions
        # Give the event loop a chance to process the cancellation.
        await asyncio.sleep(0)
        assert task.cancelled()

    async def test_eviction_keeps_fresh_sessions(self, fresh_manager: SessionManager) -> None:
        """Non-expired sessions survive eviction."""
        session = Session(session_id="fresh", username="u", api=MagicMock())
        fresh_manager._sessions["fresh"] = session
        fresh_manager._evict_expired_locked()
        assert "fresh" in fresh_manager._sessions
