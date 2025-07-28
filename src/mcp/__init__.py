"""
Model-Context Protocol (MCP) Integration Package

This folder contains the **stdio-based MCP server** used by Software Factory
to expose project tools (`get_context`, `save_spec`, etc.) to MCP-aware
coding assistants such as Claude Code, GitHub Copilot, and Cursor.

Typical usage:

```bash
# Start the server (stdio transport)
python -m src.mcp.server

# Register with Claude Code (project scope)
claude mcp add sf-server -- python -m src.mcp.server
```

Nothing in this package relies on FastAPI any longer; the previous HTTP router
has been removed in favour of the simpler, protocol-native stdio server.
"""

import logging

logger = logging.getLogger(__name__)

# Re-export the server instance for convenience (optional)
try:
    from .server import server as mcp_server  # noqa: F401
    __all__ = ["mcp_server"]
except Exception:  # pragma: no cover
    # Server import may fail during package build if dependencies are missing;
    # avoid hard failure so `pip install` still works.
    __all__: list[str] = []
