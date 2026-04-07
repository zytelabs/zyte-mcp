"""Automatic extraction MCP tools backed by Zyte API."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.models import ExtractionOptions
from zyte_mcp.tools.common import apply_common_options, normalize_response_cookies, normalize_response_headers


def _build_extraction_result(raw: dict[str, Any], field_name: str, url: str) -> dict[str, Any]:
    return {
        "url": raw.get("url", url),
        "status_code": raw.get("statusCode"),
        "data": raw.get(field_name),
        "metadata": (raw.get(field_name) or {}).get("metadata") if isinstance(raw.get(field_name), dict) else None,
        "custom_attributes": raw.get("customAttributes"),
        "response_headers": normalize_response_headers(raw),
        "response_cookies": normalize_response_cookies(raw),
        "raw": raw,
    }


def register_extraction_tools(server: FastMCP, client: ZyteClient) -> None:
    async def run_extraction(url: str, field_name: str, options: ExtractionOptions | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            field_name: True,
        }
        apply_common_options(payload, options)
        raw = await client.extract(payload)
        return _build_extraction_result(raw, field_name, url)

    @server.tool(description="Extract product data from a page")
    async def extract_product(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "product", options)

    @server.tool(description="Extract product list data from a page")
    async def extract_product_list(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "productList", options)

    @server.tool(description="Extract article data from a page")
    async def extract_article(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "article", options)

    @server.tool(description="Extract page content from a page")
    async def extract_page_content(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "pageContent", options)
