"""Device write MCP tools: update_property, update_properties."""

from connectlife.api import LifeConnectError

from ..server import mcp, session_manager
from ..session import SessionError


@mcp.tool()
async def update_property(
    session_id: str = "",
    device_id: str = "",
    property_name: str = "",
    value: str = "",
) -> dict:
    """Update a single property on an appliance.

    ``value`` is always sent as a string to the ConnectLife API.
    A local optimistic update is applied immediately so subsequent
    ``get_status`` calls reflect the change before the next poll.

    Returns the updated property and value on success, or ``error`` on failure.
    """
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    appliance = session.appliances.get(device_id)
    if appliance is None:
        return {"error": f"Device {device_id!r} not found"}
    try:
        await session.api.update_appliance(appliance.puid, {property_name: value})
        appliance.status_list[property_name] = value
    except LifeConnectError as err:
        return {"error": f"Command failed: {err}"}
    return {"device_id": device_id, "property": property_name, "value": value}


@mcp.tool()
async def update_properties(
    session_id: str = "",
    device_id: str = "",
    properties: dict[str, str] | None = None,
) -> dict:
    """Update multiple properties on an appliance in a single API call.

    ``properties`` is a mapping of property name → string value.
    Optimistic local state is updated on success.

    Returns the updated properties on success, or ``error`` on failure.
    """
    if properties is None:
        properties = {}
    try:
        session = await session_manager.resolve_session(session_id or None)
    except SessionError as err:
        return {"error": str(err)}
    appliance = session.appliances.get(device_id)
    if appliance is None:
        return {"error": f"Device {device_id!r} not found"}
    try:
        await session.api.update_appliance(appliance.puid, properties)
        appliance.status_list.update(properties)
    except LifeConnectError as err:
        return {"error": f"Command failed: {err}"}
    return {"device_id": device_id, "updated": properties}
