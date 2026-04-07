"""CLI entrypoint for the Zyte MCP server."""

from __future__ import annotations

from zyte_mcp.server import create_server


def main() -> None:
    server = create_server()
    server.run(transport="stdio")
