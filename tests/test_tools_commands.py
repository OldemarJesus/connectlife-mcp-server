"""Tests for device write tools (update_property, update_properties)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectlife_mcp.session import SessionError
from connectlife_mcp.tools import commands


@pytest.fixture
def mock_session() -> MagicMock:
    """A mocked Session with one appliance."""
    appliance = MagicMock()
    appliance.device_id = "dev-1"
    appliance.puid = "puid-1"
    appliance.status_list = {"t_power": "off"}

    session = MagicMock()
    session.appliances = {"dev-1": appliance}
    session.api = MagicMock()
    session.api.update_appliance = AsyncMock()
    return session


class TestUpdateProperty:
    async def test_success(self, mock_session: MagicMock) -> None:
        """Updating a property calls the API and optimistically mutates state."""
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await commands.update_property("", "dev-1", "t_power", "on")

        assert result == {"device_id": "dev-1", "property": "t_power", "value": "on"}
        mock_session.api.update_appliance.assert_awaited_once_with("puid-1", {"t_power": "on"})
        assert mock_session.appliances["dev-1"].status_list["t_power"] == "on"

    async def test_device_not_found(self, mock_session: MagicMock) -> None:
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await commands.update_property("", "missing", "t_power", "on")
        assert "error" in result

    async def test_api_error(self, mock_session: MagicMock) -> None:
        from connectlife.api import LifeConnectError

        mock_session.api.update_appliance = AsyncMock(side_effect=LifeConnectError("rejected"))
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await commands.update_property("", "dev-1", "t_power", "on")
        assert "error" in result
        assert "rejected" in result["error"]

    async def test_session_error(self) -> None:
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(side_effect=SessionError("expired"))
            result = await commands.update_property("", "dev-1", "t_power", "on")
        assert result == {"error": "expired"}


class TestUpdateProperties:
    async def test_success(self, mock_session: MagicMock) -> None:
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            props = {"t_power": "on", "t_temp": "5"}
            result = await commands.update_properties("", "dev-1", props)

        assert result["device_id"] == "dev-1"
        assert result["updated"] == props
        mock_session.api.update_appliance.assert_awaited_once_with("puid-1", props)
        assert mock_session.appliances["dev-1"].status_list["t_power"] == "on"
        assert mock_session.appliances["dev-1"].status_list["t_temp"] == "5"

    async def test_none_defaults_to_empty_dict(self, mock_session: MagicMock) -> None:
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await commands.update_properties("", "dev-1", None)
        assert result["updated"] == {}

    async def test_device_not_found(self, mock_session: MagicMock) -> None:
        with patch.object(commands, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await commands.update_properties("", "ghost", {"a": "b"})
        assert "error" in result
