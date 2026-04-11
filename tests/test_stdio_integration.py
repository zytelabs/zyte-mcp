from __future__ import annotations

import os
from pathlib import Path

import pytest
from mcp import ClientSession, stdio_client
from mcp.client.stdio import StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]


async def _list_stdio_tool_names(env: dict[str, str]) -> set[str]:
    params = StdioServerParameters(
        command="uv",
        args=["run", "--directory", str(ROOT), "zyte-mcp"],
        env=env,
        cwd=ROOT,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
    return {tool.name for tool in result.tools}


@pytest.mark.asyncio
async def test_stdio_lists_only_zyte_tools_without_scrapy_cloud_key():
    env = dict(os.environ)
    env["ZYTE_API_KEY"] = "test-key"
    env.pop("SCRAPY_CLOUD_API_KEY", None)
    env.pop("SHUB_APIKEY", None)

    tool_names = await _list_stdio_tool_names(env)

    assert "fetch_http" in tool_names
    assert "render_page" in tool_names
    assert "extract_product" in tool_names
    assert "scrapy_cloud_run_spider" not in tool_names
    assert "scrapy_cloud_get_logs" not in tool_names


@pytest.mark.asyncio
async def test_stdio_lists_scrapy_cloud_tools_when_key_is_present():
    env = dict(os.environ)
    env["ZYTE_API_KEY"] = "test-key"
    env["SCRAPY_CLOUD_API_KEY"] = "scrapy-key"

    tool_names = await _list_stdio_tool_names(env)

    assert "fetch_http" in tool_names
    assert "scrapy_cloud_run_spider" in tool_names
    assert "scrapy_cloud_list_jobs" in tool_names
    assert "scrapy_cloud_get_logs" in tool_names
    assert "scrapy_cloud_cancel_job" in tool_names
    assert "scrapy_cloud_list_spiders" in tool_names
