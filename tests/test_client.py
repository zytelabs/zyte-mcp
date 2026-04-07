from __future__ import annotations

import base64

import httpx
import pytest

from zyte_mcp.client import ZyteClient
from zyte_mcp.config import ZyteSettings
from zyte_mcp.errors import ZyteAPIError, ZyteRequestValidationError
from zyte_mcp.scrapy_cloud_client import ScrapyCloudClient, ScrapyCloudAPIError
from zyte_mcp.scrapy_cloud_config import ScrapyCloudSettings


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


def make_scrapy_cloud_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    settings = ScrapyCloudSettings(api_key="scrapy-key", request_timeout_seconds=1)
    return ScrapyCloudClient(settings, client=http_client)


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


@pytest.mark.asyncio
async def test_scrapy_cloud_list_jobs_uses_app_host():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://app.zyte.com/api/jobs/list.json?project=123")
        assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(200, json={"status": "ok", "jobs": []})

    client = make_scrapy_cloud_client(handler)
    result = await client.list_jobs({"project": 123})
    assert result["status"] == "ok"
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_run_job_flattens_spider_args():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert request.url == httpx.URL("https://app.zyte.com/api/run.json")
        assert "project=123" in body
        assert "spider=demo" in body
        assert "category=books" in body
        assert "spider_args=" not in body
        return httpx.Response(200, json={"status": "ok", "jobid": "123/1/1"})

    client = make_scrapy_cloud_client(handler)
    result = await client.run_job(123, {"spider": "demo", "spider_args": {"category": "books"}})
    assert result["jobid"] == "123/1/1"
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_logs_parses_json_lines():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://storage.zyte.com/logs/123/4/5")
        return httpx.Response(
            200,
            text='{"level":20,"message":"one"}\n{"level":40,"message":"two"}\n',
            headers={"content-type": "application/x-jsonlines"},
        )

    client = make_scrapy_cloud_client(handler)
    result = await client.get_logs(123, 4, 5)
    assert result[0]["message"] == "one"
    assert result[1]["level"] == 40
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_list_items_repeats_list_query_params():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://storage.zyte.com/items/1/2/3?index=4&index=5&meta=_key&meta=_ts"
        return httpx.Response(200, text='[{"name":"Widget"}]', headers={"content-type": "application/json"})

    client = make_scrapy_cloud_client(handler)
    result = await client.list_items(1, 2, 3, params={"index": [4, 5], "meta": ["_key", "_ts"]})
    assert result[0]["name"] == "Widget"
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_requests_stats_uses_storage_host():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://storage.zyte.com/requests/123/4/5/stats")
        return httpx.Response(200, json={"counts": {"url": 1}, "totals": {"input_values": 1}})

    client = make_scrapy_cloud_client(handler)
    result = await client.get_request_stats(123, 4, 5)
    assert result["totals"]["input_values"] == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_jobq_count_uses_jobq_host_and_repeated_tags():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://jobq.zyte.com/jobq/53/count?has_tag=a&has_tag=b"
        return httpx.Response(200, text="2", headers={"content-type": "text/plain"})

    client = make_scrapy_cloud_client(handler)
    result = await client.jobq_count(53, params={"has_tag": ["a", "b"]})
    assert result == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_projects_activity_supports_repeated_project_ids():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://storage.zyte.com/activity/projects?p=111&p=222&pcount=1&meta=_project"
        return httpx.Response(200, text='{"_project":111,"event":"job:completed"}', headers={"content-type": "application/x-jsonlines"})

    client = make_scrapy_cloud_client(handler)
    result = await client.get_projects_activity(params={"p": [111, 222], "pcount": 1, "meta": ["_project"]})
    assert result["_project"] == 111
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_list_comments_uses_app_host():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://app.zyte.com/api/comments/1/2/3")
        return httpx.Response(200, json={"0": [{"id": 1, "text": "hello"}]})

    client = make_scrapy_cloud_client(handler)
    result = await client.list_comments(1, 2, 3)
    assert result["0"][0]["text"] == "hello"
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_metadata_field_can_return_scalar():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='["tag1", "tag2"]', headers={"content-type": "application/json"})

    client = make_scrapy_cloud_client(handler)
    result = await client.get_job_metadata(1, 2, 3, field_name="tags")
    assert result == ["tag1", "tag2"]
    await client.aclose()


@pytest.mark.asyncio
async def test_scrapy_cloud_raises_normalized_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    client = make_scrapy_cloud_client(handler)
    with pytest.raises(ScrapyCloudAPIError) as exc:
        await client.get_logs(123, 4, 5)

    assert exc.value.status_code == 404
    await client.aclose()
