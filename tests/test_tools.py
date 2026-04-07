from __future__ import annotations

import base64

import pytest

from zyte_mcp.server import create_server


class FakeClient:
    def __init__(self):
        self.payloads = []

    async def extract(self, payload):
        self.payloads.append(payload)
        if payload.get("httpResponseBody"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "httpResponseBody": base64.b64encode(b"hello").decode("ascii"),
                "httpResponseHeaders": {"content-type": "text/plain"},
            }
        if payload.get("browserHtml"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "browserHtml": "<html></html>",
                "actions": [{"action": "click", "status": "success"}],
            }
        if payload.get("screenshot"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "screenshot": "abcd",
                "actions": [],
            }
        if payload.get("product"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "product": {"name": "Widget", "metadata": {"probability": 0.9}},
            }
        if payload.get("productList"):
            return {"url": payload["url"], "statusCode": 200, "productList": {"items": []}}
        if payload.get("article"):
            return {"url": payload["url"], "statusCode": 200, "article": {"headline": "Story"}}
        return {"url": payload["url"], "statusCode": 200, "pageContent": {"text": "hello"}}

    def decode_text_body(self, raw):
        body = raw.get("httpResponseBody")
        if not body:
            return None
        return base64.b64decode(body).decode("utf-8")


class FakeScrapyCloudClient:
    def __init__(self):
        self.calls = []

    async def run_job(self, project_id, payload):
        self.calls.append(("run_job", project_id, payload))
        return {"status": "ok", "jobid": "123/1/1"}

    async def list_jobs(self, params):
        self.calls.append(("list_jobs", params))
        return {"status": "ok", "count": 1, "total": 1, "jobs": [{"id": "123/1/1", "state": "running"}]}

    async def stop_job(self, project_id, job_id):
        self.calls.append(("stop_job", project_id, job_id))
        return {"status": "ok"}

    async def update_job_tags(self, project_id, job_id, payload):
        self.calls.append(("update_job_tags", project_id, job_id, payload))
        return {"status": "ok"}

    async def list_comments(self, project_id, spider_id, job_id):
        self.calls.append(("list_comments", project_id, spider_id, job_id))
        return {"0": [{"id": 1, "text": "needs review"}]}

    async def get_comments_stats(self, project_id):
        self.calls.append(("get_comments_stats", project_id))
        return {"123/1/1": 2}

    async def get_item_comments(self, project_id, spider_id, job_id, item_no, field_name=None):
        self.calls.append(("get_item_comments", project_id, spider_id, job_id, item_no, field_name))
        return [{"id": 1, "text": "field comment" if field_name else "item comment"}]

    async def get_job_metadata(self, project_id, spider_id, job_id, field_name=None):
        self.calls.append(("get_job_metadata", project_id, spider_id, job_id, field_name))
        if field_name:
            return ["tag1", "tag2"]
        return {"state": "finished", "spider": "demo"}

    async def list_items(self, project_id, spider_id=None, job_id=None, item_no=None, field_name=None, params=None):
        self.calls.append(("list_items", project_id, spider_id, job_id, item_no, field_name, params))
        if item_no is not None:
            return {"name": "Widget"} if field_name is None else "Widget"
        return [{"name": "Widget"}, {"name": "Gadget"}]

    async def get_item_stats(self, project_id, spider_id, job_id, all_fields=False):
        self.calls.append(("get_item_stats", project_id, spider_id, job_id, all_fields))
        return {"counts": {"name": 2}, "totals": {"input_values": 2}}

    async def get_logs(self, project_id, spider_id, job_id, params=None):
        self.calls.append(("get_logs", project_id, spider_id, job_id, params))
        return [{"level": 20, "message": "started"}]

    async def list_requests(self, project_id, spider_id=None, job_id=None, request_no=None, params=None):
        self.calls.append(("list_requests", project_id, spider_id, job_id, request_no, params))
        if request_no is not None:
            return {"url": "https://example.com", "status": 200}
        return [{"url": "https://example.com", "status": 200}]

    async def get_request_stats(self, project_id, spider_id, job_id):
        self.calls.append(("get_request_stats", project_id, spider_id, job_id))
        return {"counts": {"url": 1}, "totals": {"input_values": 1}}

    async def jobq_count(self, project_id, params=None):
        self.calls.append(("jobq_count", project_id, params))
        return 7

    async def jobq_list(self, project_id, params=None):
        self.calls.append(("jobq_list", project_id, params))
        return [{"key": "123/1/1", "ts": 111}]

    async def get_activity(self, project_id, params=None):
        self.calls.append(("get_activity", project_id, params))
        return [{"event": "job:completed", "job": "123/1/1"}]

    async def get_projects_activity(self, params=None):
        self.calls.append(("get_projects_activity", params))
        return [{"_project": 123, "event": "job:completed"}]


async def _tool_names(server):
    return {tool.name for tool in await server.list_tools(run_middleware=False)}


@pytest.fixture
def server(monkeypatch):
    fake_client = FakeClient()
    fake_scrapy_cloud_client = FakeScrapyCloudClient()
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.setenv("SCRAPY_CLOUD_API_KEY", "scrapy-key")
    import zyte_mcp.server as server_module

    monkeypatch.setattr(server_module, "ZyteClient", lambda settings: fake_client)
    monkeypatch.setattr(server_module, "ScrapyCloudClient", lambda settings: fake_scrapy_cloud_client)
    return create_server(), fake_client, fake_scrapy_cloud_client


@pytest.mark.asyncio
async def test_server_registers_only_zyte_tools_without_scrapy_cloud_key(monkeypatch):
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.delenv("SCRAPY_CLOUD_API_KEY", raising=False)

    server = create_server()
    tool_names = await _tool_names(server)

    assert "fetch_http" in tool_names
    assert "render_page" in tool_names
    assert "extract_product" in tool_names
    assert "scrapy_cloud_run_spider" not in tool_names
    assert "scrapy_cloud_get_logs" not in tool_names


def test_server_requires_zyte_api_key(monkeypatch):
    monkeypatch.delenv("ZYTE_API_KEY", raising=False)
    monkeypatch.delenv("SCRAPY_CLOUD_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ZYTE_API_KEY is required"):
        create_server()


@pytest.mark.asyncio
async def test_fetch_http_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("fetch_http", {"url": "https://example.com"})
    data = result.structured_content
    assert data["text"] == "hello"
    assert fake_client.payloads[0]["httpResponseBody"] is True


@pytest.mark.asyncio
async def test_render_page_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("render_page", {"url": "https://example.com", "include_iframes": True})
    data = result.structured_content
    assert data["browser_html"] == "<html></html>"
    assert fake_client.payloads[0]["includeIframes"] is True


@pytest.mark.asyncio
async def test_screenshot_page_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("screenshot_page", {"url": "https://example.com", "image_format": "png"})
    data = result.structured_content
    assert data["mime_type"] == "image/png"
    assert fake_client.payloads[0]["screenshotOptions"]["format"] == "png"


@pytest.mark.asyncio
async def test_extract_product_tool(server):
    app, _, _ = server
    result = await app.call_tool("extract_product", {"url": "https://example.com/product"})
    data = result.structured_content
    assert data["data"]["name"] == "Widget"
    assert data["metadata"]["probability"] == 0.9


@pytest.mark.asyncio
async def test_extract_page_content_tool(server):
    app, _, _ = server
    result = await app.call_tool("extract_page_content", {"url": "https://example.com/page"})
    data = result.structured_content
    assert data["data"]["text"] == "hello"


@pytest.mark.asyncio
async def test_scrapy_cloud_run_spider_tool(server):
    app, _, fake_scrapy_cloud_client = server
    result = await app.call_tool(
        "scrapy_cloud_run_spider",
        {"project_id": 123, "job": {"spider": "demo", "priority": 3, "spider_args": {"category": "books"}}},
    )
    data = result.structured_content
    assert data["job_id"] == "123/1/1"
    assert fake_scrapy_cloud_client.calls[0][0] == "run_job"
    assert fake_scrapy_cloud_client.calls[0][2]["spider_args"]["category"] == "books"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_jobs_tool(server):
    app, _, _ = server
    result = await app.call_tool("scrapy_cloud_list_jobs", {"project_id": 123})
    data = result.structured_content
    assert data["jobs"][0]["state"] == "running"


@pytest.mark.asyncio
async def test_scrapy_cloud_get_job_metadata_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_get_job_metadata",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["metadata"]["state"] == "finished"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_items_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_list_items",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["count_returned"] == 2


@pytest.mark.asyncio
async def test_scrapy_cloud_get_logs_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_get_logs",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["logs"][0]["message"] == "started"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_requests_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_list_requests",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["requests"][0]["status"] == 200


@pytest.mark.asyncio
async def test_scrapy_cloud_get_request_stats_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_get_request_stats",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["stats"]["totals"]["input_values"] == 1


@pytest.mark.asyncio
async def test_scrapy_cloud_jobq_list_tool(server):
    app, _, _ = server
    result = await app.call_tool("scrapy_cloud_jobq_list", {"project_id": 123})
    data = result.structured_content
    assert data["jobs"][0]["key"] == "123/1/1"


@pytest.mark.asyncio
async def test_scrapy_cloud_get_activity_tool(server):
    app, _, _ = server
    result = await app.call_tool("scrapy_cloud_get_activity", {"project_id": 123})
    data = result.structured_content
    assert data["events"][0]["event"] == "job:completed"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_comments_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_list_comments",
        {"project_id": 123, "spider_id": 1, "job_id": 1},
    )
    data = result.structured_content
    assert data["comments"]["0"][0]["text"] == "needs review"


@pytest.mark.asyncio
async def test_scrapy_cloud_get_item_comments_tool(server):
    app, _, _ = server
    result = await app.call_tool(
        "scrapy_cloud_get_item_comments",
        {"project_id": 123, "spider_id": 1, "job_id": 1, "item_no": 0, "field_name": "title"},
    )
    data = result.structured_content
    assert data["comments"][0]["text"] == "field comment"
