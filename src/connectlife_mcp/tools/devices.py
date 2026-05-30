"""Device read MCP tools: list, get, status, energy."""

from connectlife.appliance import ConnectLifeAppliance

from ..server import mcp, session_manager
from ..session import SessionError


def _appliance_summary(a: ConnectLifeAppliance) -> dict:
    return {
        "device_id": a.device_id,
        "name": a.device_nickname,
        "model": a.device_feature_name,
        "type_code": a.device_type_code,
        "feature_code": a.device_feature_code,
        "room": a.room_name,
        "online": a.offline_state == 1,
    }


@mcp.tool()
async def list_appliances(session_id: str = "") -> dict:
    """List all smart appliances linked to the ConnectLife account.

    Appliance data is refreshed automatically every 60 seconds in the background.
    Returns a list under the ``appliances`` key, or ``error`` on failure.
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    return {"appliances": [_appliance_summary(a) for a in session.appliances.values()]}


@mcp.tool()
async def get_appliance(session_id: str = "", device_id: str = "") -> dict:
    """Get details for a specific appliance by its ``device_id``.

    Returns device metadata (name, model, type/feature codes, online state),
    or ``error`` if not found.
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    appliance = session.appliances.get(device_id)
    if appliance is None:
        return {"error": f"Device {device_id!r} not found"}
    return _appliance_summary(appliance)


@mcp.tool()
async def get_status(session_id: str = "", device_id: str = "") -> dict:
    """Get the current status (all raw property values) of an appliance.

    Returns a ``status`` mapping of property name → current value.
    The property names match the ConnectLife API and the data dictionary YAML files.
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    appliance = session.appliances.get(device_id)
    if appliance is None:
        return {"error": f"Device {device_id!r} not found"}
    return {
        "device_id": device_id,
        "name": appliance.device_nickname,
        "online": appliance.offline_state == 1,
        "status": dict(appliance.status_list),
    }


@mcp.tool()
async def get_daily_energy(session_id: str = "", device_id: str = "") -> dict:
    """Get today's energy consumption in kWh for an appliance.

    Returns ``daily_energy_kwh`` (float or null if not supported by the device).
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    appliance = session.appliances.get(device_id)
    if appliance is None:
        return {"error": f"Device {device_id!r} not found"}
    try:
        kwh = await session.api.get_daily_energy_kwh(
            appliance.puid,
            appliance.device_type_code,
            appliance.device_feature_code,
        )
    except Exception as err:
        return {"error": f"Failed to fetch energy data: {err}"}
    return {"device_id": device_id, "daily_energy_kwh": kwh}
