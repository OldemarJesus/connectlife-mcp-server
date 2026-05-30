"""Tests for device read tools (list, get, status, energy)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectlife_mcp.session import SessionError
from connectlife_mcp.tools import devices


@pytest.fixture
def mock_session() -> MagicMock:
    """A mocked Session with one appliance."""
    appliance = MagicMock()
    appliance.device_id = "dev-1"
    appliance.device_nickname = "Fridge"
    appliance.device_feature_name = "Cooler"
    appliance.device_type_code = "007"
    appliance.device_feature_code = "FF"
    appliance.room_name = "Kitchen"
    appliance.offline_state = 1
    appliance.puid = "puid-1"
    appliance.status_list = {"t_temp": "3"}

    session = MagicMock()
    session.appliances = {"dev-1": appliance}
    session.api = MagicMock()
    session.api.get_daily_energy_kwh = AsyncMock(return_value=2.5)
    return session


class TestApplianceSummary:
    def test_summary_fields(self) -> None:
        """_appliance_summary extracts the expected keys."""
        a = MagicMock()
        a.device_id = "id"
        a.device_nickname = "name"
        a.device_feature_name = "model"
        a.device_type_code = "t"
        a.device_feature_code = "f"
        a.room_name = "room"
        a.offline_state = 1

        summary = devices._appliance_summary(a)
        assert summary == {
            "device_id": "id",
            "name": "name",
            "model": "model",
            "type_code": "t",
            "feature_code": "f",
            "room": "room",
            "online": True,
        }

    def test_offline_state_zero(self) -> None:
        """offline_state == 0 means offline."""
        a = MagicMock()
        a.device_id = "id"
        a.device_nickname = "name"
        a.device_feature_name = "model"
        a.device_type_code = "t"
        a.device_feature_code = "f"
        a.room_name = "room"
        a.offline_state = 0
        assert devices._appliance_summary(a)["online"] is False


class TestListAppliances:
    async def test_returns_appliances(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.list_appliances("")
        assert "appliances" in result
        assert len(result["appliances"]) == 1
        assert result["appliances"][0]["device_id"] == "dev-1"

    async def test_session_error(self) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(side_effect=SessionError("nope"))
            result = await devices.list_appliances("")
        assert result == {"error": "nope"}


class TestGetAppliance:
    async def test_found(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_appliance("", "dev-1")
        assert result["device_id"] == "dev-1"

    async def test_not_found(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_appliance("", "missing")
        assert "error" in result
        assert "missing" in result["error"]


class TestGetStatus:
    async def test_returns_status(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_status("", "dev-1")
        assert result["device_id"] == "dev-1"
        assert result["status"] == {"t_temp": "3"}
        assert result["online"] is True

    async def test_device_not_found(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_status("", "missing")
        assert "error" in result


class TestGetDailyEnergy:
    async def test_success(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_daily_energy("", "dev-1")
        assert result["device_id"] == "dev-1"
        assert result["daily_energy_kwh"] == 2.5

    async def test_api_failure(self, mock_session: MagicMock) -> None:
        mock_session.api.get_daily_energy_kwh = AsyncMock(side_effect=RuntimeError("api down"))
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_daily_energy("", "dev-1")
        assert "error" in result
        assert "api down" in result["error"]

    async def test_device_not_found(self, mock_session: MagicMock) -> None:
        with patch.object(devices, "session_manager") as mgr:
            mgr.resolve_session = AsyncMock(return_value=mock_session)
            result = await devices.get_daily_energy("", "ghost")
        assert "error" in result
