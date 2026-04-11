from __future__ import annotations

import base64

import httpx
import pytest

from zyte_mcp.client import ZyteClient
from zyte_mcp.config import ZyteSettings
from zyte_mcp.errors import ZyteAPIError, ZyteRequestValidationError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    settings = ZyteSettings(
        api_key="test-key",
        request_timeout_seconds=1,
        rate_limit_max_retries=0,
        download_error_max_retries=0,
    )
    return ZyteClient(settings, client=http_client)


@pytest.mark.asyncio
async def test_extract_success_returns_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.zyte.com/v1/extract")
        assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(200, json={"statusCode": 200, "url": "https://example.com"})

    client = make_client(handler)
    result = await client.extract({"url": "https://example.com", "httpResponseBody": True})
    assert result["statusCode"] == 200
    await client.aclose()


@pytest.mark.asyncio
async def test_extract_raises_zyte_error_on_failure():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"type": "/request/unprocessable", "detail": "bad combo"})

    client = make_client(handler)
    with pytest.raises(ZyteAPIError) as exc:
        await client.extract({"url": "https://example.com", "httpResponseBody": True})

    assert exc.value.status_code == 422
    assert exc.value.error_type == "/request/unprocessable"
    await client.aclose()


def test_decode_text_body_returns_utf8_text():
    client = ZyteClient(ZyteSettings(api_key="test-key"), client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))))
    raw = {
        "httpResponseBody": base64.b64encode(b'{"hello":"world"}').decode("ascii"),
        "httpResponseHeaders": {"content-type": "application/json"},
    }
    assert client.decode_text_body(raw) == '{"hello":"world"}'


def test_validate_payload_rejects_browser_http_mix():
    with pytest.raises(ZyteRequestValidationError):
        ZyteClient._validate_payload(
            {
                "url": "https://example.com",
                "browserHtml": True,
                "httpResponseBody": True,
            }
        )


def test_validate_payload_rejects_custom_attributes_without_extraction():
    with pytest.raises(ZyteRequestValidationError):
        ZyteClient._validate_payload(
            {
                "url": "https://example.com",
                "customAttributes": {"foo": {"type": "string"}},
            }
        )
