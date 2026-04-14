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
        if payload.get("productNavigation"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "productNavigation": {
                    "url": payload["url"],
                    "categoryName": "Electronics",
                    "nextPage": {"url": "https://example.com/products?page=2", "name": "Next"},
                    "pageNumber": 1,
                    "items": [{"url": "https://example.com/product/1", "name": "Widget", "metadata": {"probability": 0.95}}],
                    "subCategories": [],
                    "metadata": {"dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("articleList"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "articleList": {
                    "url": payload["url"],
                    "articles": [
                        {
                            "url": "https://example.com/article/1",
                            "headline": "Breaking News",
                            "metadata": {"probability": 0.98},
                        }
                    ],
                    "metadata": {"dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("articleNavigation"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "articleNavigation": {
                    "url": payload["url"],
                    "nextPage": {"url": "https://example.com/news?page=2", "name": "Next"},
                    "pageNumber": 1,
                    "items": [{"url": "https://example.com/article/1", "name": "Breaking News", "metadata": {"probability": 0.97}}],
                    "metadata": {"dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("forumThread"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "forumThread": {
                    "url": payload["url"],
                    "topic": {"name": "How do I do X?"},
                    "posts": [
                        {
                            "text": "Here is how you do X.",
                            "datePublished": "2024-01-01T10:00:00Z",
                            "reactions": {"likes": 5, "replies": 2},
                            "metadata": {"probability": 0.99},
                        }
                    ],
                    "metadata": {"dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("jobPosting"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "jobPosting": {
                    "url": payload["url"],
                    "jobTitle": "Senior Engineer",
                    "hiringOrganization": {"name": "Acme Corp"},
                    "jobLocation": {"raw": "Remote"},
                    "description": "Build great things.",
                    "metadata": {"probability": 0.96, "dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("jobPostingNavigation"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "jobPostingNavigation": {
                    "url": payload["url"],
                    "nextPage": {"url": "https://example.com/jobs?page=2", "name": "Next"},
                    "pageNumber": 1,
                    "items": [{"url": "https://example.com/jobs/1", "name": "Senior Engineer", "metadata": {"probability": 0.94}}],
                    "metadata": {"dateDownloaded": "2024-01-01T00:00:00Z"},
                },
            }
        if payload.get("serp"):
            return {
                "url": payload["url"],
                "statusCode": 200,
                "serp": {
                    "url": payload["url"],
                    "pageNumber": 1,
                    "organicResults": [
                        {"name": "Example", "url": "https://example.com", "description": "An example site", "rank": 1},
                        {"name": "Another", "url": "https://another.com", "description": "Another site", "rank": 2},
                    ],
                    "metadata": {
                        "displayedQuery": "test query",
                        "searchedQuery": "test query",
                        "totalOrganicResults": 1000000,
                        "dateDownloaded": "2024-01-01T00:00:00Z",
                    },
                },
            }
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




@pytest.mark.asyncio
async def test_extract_serp_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_serp", {"url": "https://www.google.com/search?q=test+query", "pages": 1})
    data = result.structured_content

    # Correct payload sent to Zyte API
    payload = fake_client.payloads[-1]
    assert payload["serp"] is True
    # browserHtml is the new default — serpOptions must be present
    assert payload["serpOptions"]["extractFrom"] == "browserHtml"

    # Response structure (multi-page format)
    assert data["pages_fetched"] == 1
    assert data["status_codes"] == [200]
    assert len(data["organic_results"]) == 2
    assert data["organic_results"][0]["name"] == "Example"
    assert data["organic_results"][0]["rank"] == 1
    assert data["metadata"]["searchedQuery"] == "test query"
    assert data["metadata"]["totalOrganicResults"] == 1000000


@pytest.mark.asyncio
async def test_extract_serp_default_pages(server):
    """extract_serp fetches 5 pages by default."""
    app, fake_client, _ = server
    await app.call_tool("extract_serp", {"url": "https://www.google.com/search?q=test"})
    # 5 payloads should have been sent (one per page)
    serp_payloads = [p for p in fake_client.payloads if p.get("serp")]
    assert len(serp_payloads) == 5
    # Page 1 has no start param; page 2 onwards has start=10,20,...
    assert "start" not in serp_payloads[0]["url"]
    assert "start=10" in serp_payloads[1]["url"]
    assert "start=20" in serp_payloads[2]["url"]


@pytest.mark.asyncio
async def test_extract_serp_with_options(server):
    app, fake_client, _ = server
    result = await app.call_tool(
        "extract_serp",
        {
            "url": "https://www.google.com/search?q=test",
            "pages": 1,
            "options": {"extract_from": "browserHtml", "include_iframes": True},
        },
    )
    data = result.structured_content

    payload = fake_client.payloads[-1]
    assert payload["serp"] is True
    assert payload["serpOptions"]["extractFrom"] == "browserHtml"
    assert payload["serpOptions"]["includeIframes"] is True
    assert data["pages_fetched"] == 1
    assert len(data["organic_results"]) == 2


@pytest.mark.asyncio
async def test_extract_serp_extract_from_only(server):
    """extract_from can be overridden to httpResponseBody."""
    app, fake_client, _ = server
    await app.call_tool(
        "extract_serp",
        {
            "url": "https://www.google.com/search?q=test",
            "pages": 1,
            "options": {"extract_from": "httpResponseBody"},
        },
    )
    payload = fake_client.payloads[-1]
    assert payload["serpOptions"]["extractFrom"] == "httpResponseBody"
    # include_iframes defaulting to False should not be sent
    assert "includeIframes" not in payload["serpOptions"]


@pytest.mark.asyncio
async def test_extract_serp_registered_in_tool_list(server):
    app, _, _ = server
    tool_names = await _tool_names(app)
    assert "extract_serp" in tool_names


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


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_uses_github_version(deploy_server, monkeypatch, tmp_path):
    """When GitHub returns the latest release, the stack in scrapinghub.yml uses it."""
    call_count = 0
    fake_stdout = (
        b'Packing version 1234-master\n'
        b'Deploying to Scrapy Cloud project "99999"\n'
    )

    async def fake_subprocess(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        proc = MagicMock()
        proc.returncode = 0
        if call_count == 1:
            proc.communicate = AsyncMock(return_value=(b"shub, version 1.0", b""))
        else:
            proc.communicate = AsyncMock(return_value=(fake_stdout, b""))
        return proc

    # Patch _fetch_latest_scrapy_version to return a fixed latest version.
    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy._fetch_latest_scrapy_version",
        return_value="2.15",
    ):
        with patch(
            "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            (tmp_path / "scrapy.cfg").touch()
            (tmp_path / "pyproject.toml").write_text(
                '[project]\ndependencies = ["scrapy>=2.14.2"]\n', encoding="utf-8"
            )
            result = await deploy_server.call_tool(
                "scrapy_cloud_deploy",
                {"project_path": str(tmp_path), "project_id": 99999},
            )

    data = result.structured_content
    assert data["success"] is True
    yml_content = (tmp_path / "scrapinghub.yml").read_text()
    # GitHub version (2.15) must take precedence over pyproject.toml version (2.14)
    assert "stack: scrapy:2.15" in yml_content
    assert "scrapy:2.14" not in yml_content


@pytest.mark.asyncio
async def test_scrapy_cloud_deploy_falls_back_when_github_unavailable(deploy_server, tmp_path):
    """When GitHub is unreachable, the stack falls back to pyproject.toml version."""
    call_count = 0
    fake_stdout = (
        b'Packing version 1234-master\n'
        b'Deploying to Scrapy Cloud project "99999"\n'
    )

    async def fake_subprocess(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        proc = MagicMock()
        proc.returncode = 0
        if call_count == 1:
            proc.communicate = AsyncMock(return_value=(b"shub, version 1.0", b""))
        else:
            proc.communicate = AsyncMock(return_value=(fake_stdout, b""))
        return proc

    # Patch _fetch_latest_scrapy_version to simulate GitHub being unreachable.
    with patch(
        "zyte_mcp.tools.scrapy_cloud_deploy._fetch_latest_scrapy_version",
        return_value=None,
    ):
        with patch(
            "zyte_mcp.tools.scrapy_cloud_deploy.asyncio.create_subprocess_exec",
            side_effect=fake_subprocess,
        ):
            (tmp_path / "scrapy.cfg").touch()
            (tmp_path / "pyproject.toml").write_text(
                '[project]\ndependencies = ["scrapy>=2.14.2"]\n', encoding="utf-8"
            )
            result = await deploy_server.call_tool(
                "scrapy_cloud_deploy",
                {"project_path": str(tmp_path), "project_id": 99999},
            )

    data = result.structured_content
    assert data["success"] is True
    yml_content = (tmp_path / "scrapinghub.yml").read_text()
    # Falls back to pyproject.toml-derived version
    assert "stack: scrapy:2.14" in yml_content


# --- new extraction type tests ---


@pytest.mark.asyncio
async def test_extract_product_navigation_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_product_navigation", {"url": "https://example.com/category"})
    data = result.structured_content
    assert fake_client.payloads[-1]["productNavigation"] is True
    assert data["data"]["categoryName"] == "Electronics"
    assert data["data"]["nextPage"]["url"] == "https://example.com/products?page=2"
    assert data["data"]["items"][0]["name"] == "Widget"
    assert data["metadata"]["dateDownloaded"] == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_extract_article_list_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_article_list", {"url": "https://example.com/news"})
    data = result.structured_content
    assert fake_client.payloads[-1]["articleList"] is True
    assert data["data"]["articles"][0]["headline"] == "Breaking News"
    assert data["data"]["articles"][0]["metadata"]["probability"] == 0.98
    assert data["metadata"]["dateDownloaded"] == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_extract_article_navigation_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_article_navigation", {"url": "https://example.com/news"})
    data = result.structured_content
    assert fake_client.payloads[-1]["articleNavigation"] is True
    assert data["data"]["nextPage"]["url"] == "https://example.com/news?page=2"
    assert data["data"]["pageNumber"] == 1
    assert data["data"]["items"][0]["name"] == "Breaking News"
    assert data["metadata"]["dateDownloaded"] == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_extract_forum_thread_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_forum_thread", {"url": "https://forum.example.com/thread/1"})
    data = result.structured_content
    assert fake_client.payloads[-1]["forumThread"] is True
    assert data["data"]["topic"]["name"] == "How do I do X?"
    assert data["data"]["posts"][0]["text"] == "Here is how you do X."
    assert data["data"]["posts"][0]["reactions"]["likes"] == 5
    assert data["metadata"]["dateDownloaded"] == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_extract_job_posting_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_job_posting", {"url": "https://jobs.example.com/job/1"})
    data = result.structured_content
    assert fake_client.payloads[-1]["jobPosting"] is True
    assert data["data"]["jobTitle"] == "Senior Engineer"
    assert data["data"]["hiringOrganization"]["name"] == "Acme Corp"
    assert data["metadata"]["probability"] == 0.96


@pytest.mark.asyncio
async def test_extract_job_posting_navigation_tool(server):
    app, fake_client, _ = server
    result = await app.call_tool("extract_job_posting_navigation", {"url": "https://jobs.example.com"})
    data = result.structured_content
    assert fake_client.payloads[-1]["jobPostingNavigation"] is True
    assert data["data"]["nextPage"]["url"] == "https://example.com/jobs?page=2"
    assert data["data"]["pageNumber"] == 1
    assert data["data"]["items"][0]["name"] == "Senior Engineer"
    assert data["metadata"]["dateDownloaded"] == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_new_extraction_tools_registered(server):
    app, _, _ = server
    tool_names = await _tool_names(app)
    assert "extract_product_navigation" in tool_names
    assert "extract_article_list" in tool_names
    assert "extract_article_navigation" in tool_names
    assert "extract_forum_thread" in tool_names
    assert "extract_job_posting" in tool_names
    assert "extract_job_posting_navigation" in tool_names
