"""FastMCP server construction."""

from __future__ import annotations

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.config import get_settings
from zyte_mcp.scrapy_cloud_client import ScrapyCloudClient
from zyte_mcp.scrapy_cloud_config import get_scrapy_cloud_settings_optional
from zyte_mcp.tools import (
    register_browser_tools,
    register_extraction_tools,
    register_http_tools,
    register_scrapy_cloud_jobs_tools,
    register_scrapy_cloud_storage_tools,
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

    scrapy_cloud_settings = get_scrapy_cloud_settings_optional()
    if scrapy_cloud_settings is not None:
        scrapy_cloud_client = ScrapyCloudClient(scrapy_cloud_settings)
        register_scrapy_cloud_jobs_tools(server, scrapy_cloud_client)
        register_scrapy_cloud_storage_tools(server, scrapy_cloud_client)

    return server
