"""HTTP-oriented MCP tools backed by Zyte API."""

from __future__ import annotations

import base64
from typing import Any

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.models import ZyteRequestOptions
from zyte_mcp.tools.common import apply_common_options, normalize_response_cookies, normalize_response_headers


def register_http_tools(server: FastMCP, client: ZyteClient) -> None:
    @server.tool(description="Fetch a URL through Zyte HTTP mode")
    async def fetch_http(
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body_text: str | None = None,
        body_base64: str | None = None,
        options: ZyteRequestOptions | None = None,
    ) -> dict[str, Any]:
        if body_text is not None and body_base64 is not None:
            raise ValueError("Provide only one of body_text or body_base64")

        payload: dict[str, Any] = {
            "url": url,
            "httpResponseBody": True,
            "httpRequestMethod": method.upper(),
        }
        if headers:
            payload["requestHeaders"] = headers
        if body_text is not None:
            payload["httpRequestBody"] = base64.b64encode(body_text.encode("utf-8")).decode("ascii")
        elif body_base64 is not None:
            payload["httpRequestBody"] = body_base64

        apply_common_options(payload, options)

        raw = await client.extract(payload)
        headers_out = normalize_response_headers(raw)
        return {
            "url": raw.get("url", url),
            "status_code": raw.get("statusCode"),
            "content_type": (headers_out or {}).get("content-type") or (headers_out or {}).get("Content-Type"),
            "text": client.decode_text_body(raw),
            "body_base64": raw.get("httpResponseBody"),
            "response_headers": headers_out,
            "response_cookies": normalize_response_cookies(raw),
            "raw": raw,
        }
