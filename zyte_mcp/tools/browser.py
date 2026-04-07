"""Browser-oriented MCP tools backed by Zyte API."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.models import BrowserAction, ZyteRequestOptions
from zyte_mcp.tools.common import (
    apply_common_options,
    normalize_response_cookies,
    normalize_response_headers,
    serialize_actions,
)


def register_browser_tools(server: FastMCP, client: ZyteClient) -> None:
    @server.tool(description="Render a page through Zyte browser mode")
    async def render_page(
        url: str,
        actions: list[BrowserAction] | None = None,
        include_iframes: bool = False,
        javascript: bool | None = None,
        referer: str | None = None,
        options: ZyteRequestOptions | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "browserHtml": True,
        }
        action_list = serialize_actions(actions)
        if action_list:
            payload["actions"] = action_list
        if include_iframes:
            payload["includeIframes"] = True
        if javascript is not None:
            payload["javascript"] = javascript
        if referer:
            payload["requestHeaders"] = {"referer": referer}

        apply_common_options(payload, options)
        raw = await client.extract(payload)

        return {
            "url": raw.get("url", url),
            "status_code": raw.get("statusCode"),
            "browser_html": raw.get("browserHtml"),
            "actions": raw.get("actions"),
            "response_headers": normalize_response_headers(raw),
            "response_cookies": normalize_response_cookies(raw),
            "raw": raw,
        }

    @server.tool(description="Capture a screenshot through Zyte browser mode")
    async def screenshot_page(
        url: str,
        actions: list[BrowserAction] | None = None,
        image_format: Literal["jpeg", "png"] = "jpeg",
        full_page: bool = False,
        javascript: bool | None = None,
        referer: str | None = None,
        options: ZyteRequestOptions | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "screenshot": True,
            "screenshotOptions": {
                "format": image_format,
                "fullPage": full_page,
            },
        }
        action_list = serialize_actions(actions)
        if action_list:
            payload["actions"] = action_list
        if javascript is not None:
            payload["javascript"] = javascript
        if referer:
            payload["requestHeaders"] = {"referer": referer}

        apply_common_options(payload, options)
        raw = await client.extract(payload)

        return {
            "url": raw.get("url", url),
            "status_code": raw.get("statusCode"),
            "mime_type": f"image/{image_format}",
            "image_base64": raw.get("screenshot"),
            "actions": raw.get("actions"),
            "raw": raw,
        }
