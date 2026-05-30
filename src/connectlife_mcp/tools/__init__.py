"""Tool registration package — importing this module registers all MCP tools."""

# Import each tool module so their @mcp.tool() decorators fire.
from . import auth, commands, devices

__all__ = ["auth", "commands", "devices"]
