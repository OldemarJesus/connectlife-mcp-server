"""Shared fixtures for ConnectLife MCP server tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from connectlife_mcp.session import Session, SessionManager


@pytest.fixture
def utcnow() -> datetime:
    """A frozen UTC timestamp for deterministic tests."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_api() -> MagicMock:
    """A mocked ConnectLifeApi with common attributes."""
    api = MagicMock()
    api.appliances = []
    api.get_daily_energy_kwh = AsyncMock(return_value=1.23)
    api.update_appliance = AsyncMock()
    api.authenticate = AsyncMock(return_value=True)
    api.login = AsyncMock()
    api.get_appliances = AsyncMock()
    return api


@pytest.fixture
def fake_appliance() -> MagicMock:
    """A single mocked appliance."""
    app = MagicMock()
    app.device_id = "DEV-001"
    app.device_nickname = "Test Fridge"
    app.device_feature_name = "SmartFridge"
    app.device_type_code = "123"
    app.device_feature_code = "ABC"
    app.room_name = "Kitchen"
    app.offline_state = 1
    app.puid = "puid-001"
    app.status_list = {"t_temp": "4", "t_power": "on"}
    return app


@pytest.fixture
def session_manager() -> SessionManager:
    """A fresh SessionManager instance."""
    return SessionManager()


@pytest.fixture
async def session_with_appliance(
    session_manager: SessionManager,
    mock_api: MagicMock,
    fake_appliance: MagicMock,
) -> AsyncGenerator[Session]:
    """Inject a session with one appliance into the manager."""
    mock_api.appliances = [fake_appliance]
    session = Session(
        session_id="sess-test-123",
        username="tester",
        api=mock_api,
        appliances={fake_appliance.device_id: fake_appliance},
    )
    async with session_manager._lock:
        session_manager._sessions[session.session_id] = session
    yield session
    async with session_manager._lock:
        session_manager._sessions.pop(session.session_id, None)
