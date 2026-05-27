"""FastMCP server construction."""

from __future__ import annotations

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.config import get_settings
from zyte_mcp.scrapy_cloud_config import get_scrapy_cloud_client_optional
from zyte_mcp.tools import (
    register_browser_tools,
    register_extraction_tools,
    register_http_tools,
    # register_schema_tools,  # not ready for use yet
    register_scrapy_cloud_jobs_tools,
    register_scrapy_cloud_storage_tools,
    register_search_tools,
)


def create_server() -> FastMCP:
    settings = get_settings()
    client = ZyteClient(settings)
    server = FastMCP(
        name="zyte-mcp",
        instructions="Task-focused MCP server for Zyte API and Scrapy Cloud workflows.",
    )

    register_http_tools(server, client)
    register_browser_tools(server, client)
    register_extraction_tools(server, client)
    register_search_tools(server, client)

    # Schema tools are not ready for use yet — kept here for future re-enabling
    # anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    # if anthropic_api_key:
    #     from anthropic import AsyncAnthropic
    #     anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
    #     register_schema_tools(server, client, anthropic_client)

    scrapy_cloud_client = get_scrapy_cloud_client_optional()
    if scrapy_cloud_client is not None:
        register_scrapy_cloud_jobs_tools(server, scrapy_cloud_client)
        register_scrapy_cloud_storage_tools(server, scrapy_cloud_client)

    return server
