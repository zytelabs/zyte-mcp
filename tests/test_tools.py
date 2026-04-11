from __future__ import annotations

import asyncio
import base64
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_fake_sc_client():
    """Build a MagicMock ScrapinghubClient with the structure the tools expect."""
    sc = MagicMock()

    # project mock
    project = MagicMock()
    sc.get_project.return_value = project

    # jobs.run returns a job with a key
    run_job = MagicMock()
    run_job.key = "123/1/1"
    project.jobs.run.return_value = run_job

    # jobs.iter returns a list of job summaries
    project.jobs.iter.return_value = iter([{"key": "123/1/1", "state": "running"}])

    # jobs.count
    project.jobs.count.return_value = 3

    # spiders.list
    project.spiders.list.return_value = [{"id": "demo"}, {"id": "other"}]

    # activity.iter
    project.activity.iter.return_value = iter([{"event": "job:completed", "job": "123/1/1"}])

    # job mock
    job = MagicMock()
    sc.get_job.return_value = job

    # metadata
    job.metadata.iter.return_value = iter([("state", "finished"), ("spider", "demo")])
    job.metadata.get.return_value = ["tag1", "tag2"]

    # items
    job.items.iter.return_value = iter([{"name": "Widget"}, {"name": "Gadget"}])

    # logs
    job.logs.iter.return_value = iter([{"level": 20, "message": "started"}])

    # requests
    job.requests.iter.return_value = iter([{"url": "https://example.com", "status": 200}])

    return sc


async def _tool_names(server):
    return {tool.name for tool in await server.list_tools(run_middleware=False)}


@pytest.fixture
def server(monkeypatch):
    fake_client = FakeClient()
    fake_sc_client = _make_fake_sc_client()
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.setenv("SCRAPY_CLOUD_API_KEY", "scrapy-key")
    import zyte_mcp.server as server_module

    monkeypatch.setattr(server_module, "ZyteClient", lambda settings: fake_client)
    monkeypatch.setattr(server_module, "get_scrapy_cloud_client_optional", lambda: fake_sc_client)
    return create_server(), fake_client, fake_sc_client


@pytest.mark.asyncio
async def test_server_registers_only_zyte_tools_without_scrapy_cloud_key(monkeypatch):
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.delenv("SCRAPY_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("SHUB_APIKEY", raising=False)

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
    monkeypatch.delenv("SHUB_APIKEY", raising=False)

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
    app, _, fake_sc = server
    result = await app.call_tool(
        "scrapy_cloud_run_spider",
        {"project_id": 123, "spider": "demo", "job_args": {"category": "books"}},
    )
    data = result.structured_content
    assert data["job_key"] == "123/1/1"
    fake_sc.get_project.assert_called_with(123)
    fake_sc.get_project(123).jobs.run.assert_called_once_with("demo", job_args={"category": "books"})


@pytest.mark.asyncio
async def test_scrapy_cloud_list_jobs_tool(server):
    app, _, fake_sc = server
    # reset iter so it's fresh
    fake_sc.get_project(123).jobs.iter.return_value = iter([{"key": "123/1/1", "state": "running"}])
    result = await app.call_tool("scrapy_cloud_list_jobs", {"project_id": 123})
    data = result.structured_content
    assert data["jobs"][0]["state"] == "running"
    assert data["count_returned"] == 1


@pytest.mark.asyncio
async def test_scrapy_cloud_cancel_job_tool(server):
    app, _, fake_sc = server
    result = await app.call_tool("scrapy_cloud_cancel_job", {"job_key": "123/1/1"})
    data = result.structured_content
    assert data["cancelled"] is True
    assert data["job_key"] == "123/1/1"


@pytest.mark.asyncio
async def test_scrapy_cloud_update_job_tags_tool(server):
    app, _, fake_sc = server
    result = await app.call_tool(
        "scrapy_cloud_update_job_tags",
        {"job_key": "123/1/1", "add": ["reviewed"], "remove": ["pending"]},
    )
    data = result.structured_content
    assert data["updated"] is True


@pytest.mark.asyncio
async def test_scrapy_cloud_get_job_metadata_tool(server):
    app, _, fake_sc = server
    fake_sc.get_job("123/1/1").metadata.iter.return_value = iter([("state", "finished"), ("spider", "demo")])
    result = await app.call_tool("scrapy_cloud_get_job_metadata", {"job_key": "123/1/1"})
    data = result.structured_content
    assert data["metadata"]["state"] == "finished"


@pytest.mark.asyncio
async def test_scrapy_cloud_get_job_metadata_field_tool(server):
    app, _, fake_sc = server
    fake_sc.get_job("123/1/1").metadata.get.return_value = ["tag1", "tag2"]
    result = await app.call_tool(
        "scrapy_cloud_get_job_metadata_field",
        {"job_key": "123/1/1", "field_name": "tags"},
    )
    data = result.structured_content
    assert data["value"] == ["tag1", "tag2"]
    assert data["field_name"] == "tags"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_items_tool(server):
    app, _, fake_sc = server
    fake_sc.get_job("123/1/1").items.iter.return_value = iter([{"name": "Widget"}, {"name": "Gadget"}])
    result = await app.call_tool("scrapy_cloud_list_items", {"job_key": "123/1/1"})
    data = result.structured_content
    assert data["count_returned"] == 2
    assert data["items"][0]["name"] == "Widget"


@pytest.mark.asyncio
async def test_scrapy_cloud_get_logs_tool(server):
    app, _, fake_sc = server
    fake_sc.get_job("123/1/1").logs.iter.return_value = iter([{"level": 20, "message": "started"}])
    result = await app.call_tool("scrapy_cloud_get_logs", {"job_key": "123/1/1"})
    data = result.structured_content
    assert data["logs"][0]["message"] == "started"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_requests_tool(server):
    app, _, fake_sc = server
    fake_sc.get_job("123/1/1").requests.iter.return_value = iter([{"url": "https://example.com", "status": 200}])
    result = await app.call_tool("scrapy_cloud_list_requests", {"job_key": "123/1/1"})
    data = result.structured_content
    assert data["requests"][0]["status"] == 200


@pytest.mark.asyncio
async def test_scrapy_cloud_count_jobs_tool(server):
    app, _, fake_sc = server
    fake_sc.get_project(123).jobs.count.return_value = 3
    result = await app.call_tool("scrapy_cloud_count_jobs", {"project_id": 123, "state": "running"})
    data = result.structured_content
    assert data["count"] == 3


@pytest.mark.asyncio
async def test_scrapy_cloud_get_activity_tool(server):
    app, _, fake_sc = server
    fake_sc.get_project(123).activity.iter.return_value = iter([{"event": "job:completed", "job": "123/1/1"}])
    result = await app.call_tool("scrapy_cloud_get_activity", {"project_id": 123})
    data = result.structured_content
    assert data["events"][0]["event"] == "job:completed"


@pytest.mark.asyncio
async def test_scrapy_cloud_list_spiders_tool(server):
    app, _, fake_sc = server
    fake_sc.get_project(123).spiders.list.return_value = [{"id": "demo"}, {"id": "other"}]
    result = await app.call_tool("scrapy_cloud_list_spiders", {"project_id": 123})
    data = result.structured_content
    assert data["count_returned"] == 2
    assert data["spiders"][0]["id"] == "demo"


# --- scrapy_cloud_deploy tests ---


@pytest.fixture
def deploy_server(monkeypatch):
    """Server fixture with only Zyte tools + deploy tool (no SC client)."""
    fake_client = FakeClient()
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")
    monkeypatch.delenv("SCRAPY_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("SHUB_APIKEY", raising=False)
    import zyte_mcp.server as server_module

    monkeypatch.setattr(server_module, "ZyteClient", lambda settings: fake_client)
    monkeypatch.setattr(server_module, "get_scrapy_cloud_client_optional", lambda: None)
    return create_server()


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_shub_not_installed(deploy_server, monkeypatch):
    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError,
    ):
        result = await deploy_server.call_tool(
            "scrapy_cloud_deploy", {"project_path": "/some/project"}
        )
    data = result.structured_content
    assert data["ready"] is False
    assert data["issue"] == "shub_not_installed"
    assert "pip install shub" in data["fix"]


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_missing_scrapy_cfg(deploy_server):
    # Mock shub --version succeeding
    version_proc = MagicMock()
    version_proc.returncode = 0
    version_proc.communicate = AsyncMock(return_value=(b"shub, version 1.0", b""))

    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
        return_value=version_proc,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            # tmpdir has no scrapy.cfg
            result = await deploy_server.call_tool(
                "scrapy_cloud_deploy", {"project_path": tmpdir}
            )
    data = result.structured_content
    assert data["ready"] is False
    assert data["issue"] == "not_a_scrapy_project"


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_missing_yaml_and_no_project_id(deploy_server):
    version_proc = MagicMock()
    version_proc.returncode = 0
    version_proc.communicate = AsyncMock(return_value=(b"shub, version 1.0", b""))

    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
        return_value=version_proc,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "scrapy.cfg").touch()
            # no scrapinghub.yml, no project_id
            result = await deploy_server.call_tool(
                "scrapy_cloud_deploy", {"project_path": tmpdir}
            )
    data = result.structured_content
    assert data["ready"] is False
    assert data["issue"] == "missing_scrapinghub_yml"
    assert "https://app.zyte.com/" in data["action_required"]
    assert "project_id" in data["action_required"]
    assert "template" in data


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_success(deploy_server):
    call_count = 0
    fake_stdout = (
        b'Packing version 1234-master\n'
        b'Deploying to Scrapy Cloud project "12345"\n'
        b'Run your spiders at: https://app.zyte.com/p/12345/\n'
    )

    async def fake_subprocess(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        proc = MagicMock()
        proc.returncode = 0
        if call_count == 1:
            # shub --version
            proc.communicate = AsyncMock(return_value=(b"shub, version 1.0", b""))
        else:
            # shub deploy
            proc.communicate = AsyncMock(return_value=(fake_stdout, b""))
        return proc

    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
        side_effect=fake_subprocess,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "scrapy.cfg").touch()
            Path(tmpdir, "scrapinghub.yml").write_text("projects:\n  default: 12345\n")
            result = await deploy_server.call_tool(
                "scrapy_cloud_deploy", {"project_path": tmpdir}
            )
    data = result.structured_content
    assert data["success"] is True
    assert data["project_id"] == 12345
    assert data["version"] == "1234-master"
    assert "https://app.zyte.com/p/12345/" in data["stdout"]
