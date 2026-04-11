"""Scrapy Cloud storage read tools."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP
from scrapinghub import ScrapinghubClient


def register_scrapy_cloud_storage_tools(server: FastMCP, client: ScrapinghubClient) -> None:
    @server.tool(description="Get all metadata for a Scrapy Cloud job")
    async def scrapy_cloud_get_job_metadata(job_key: str) -> dict[str, Any]:
        def _get():
            return dict(client.get_job(job_key).metadata.iter())

        metadata = await asyncio.to_thread(_get)
        return {
            "job_key": job_key,
            "metadata": metadata,
        }

    @server.tool(description="Get one metadata field for a Scrapy Cloud job")
    async def scrapy_cloud_get_job_metadata_field(job_key: str, field_name: str) -> dict[str, Any]:
        def _get():
            return client.get_job(job_key).metadata.get(field_name)

        value = await asyncio.to_thread(_get)
        return {
            "job_key": job_key,
            "field_name": field_name,
            "value": value,
        }

    @server.tool(description="List scraped items from a Scrapy Cloud job")
    async def scrapy_cloud_list_items(
        job_key: str,
        count: int | None = None,
        start: int | None = None,
    ) -> dict[str, Any]:
        def _list():
            kwargs: dict[str, Any] = {}
            if count is not None:
                kwargs["count"] = count
            if start is not None:
                kwargs["start"] = start
            return list(client.get_job(job_key).items.iter(**kwargs))

        items = await asyncio.to_thread(_list)
        return {
            "job_key": job_key,
            "items": items,
            "count_returned": len(items),
        }

    @server.tool(description="Get log entries for a Scrapy Cloud job")
    async def scrapy_cloud_get_logs(
        job_key: str,
        count: int | None = None,
    ) -> dict[str, Any]:
        def _get():
            kwargs: dict[str, Any] = {}
            if count is not None:
                kwargs["count"] = count
            return list(client.get_job(job_key).logs.iter(**kwargs))

        logs = await asyncio.to_thread(_get)
        return {
            "job_key": job_key,
            "logs": logs,
            "count_returned": len(logs),
        }

    @server.tool(description="List HTTP request records for a Scrapy Cloud job")
    async def scrapy_cloud_list_requests(
        job_key: str,
        count: int | None = None,
        start: int | None = None,
    ) -> dict[str, Any]:
        def _list():
            kwargs: dict[str, Any] = {}
            if count is not None:
                kwargs["count"] = count
            if start is not None:
                kwargs["start"] = start
            return list(client.get_job(job_key).requests.iter(**kwargs))

        requests = await asyncio.to_thread(_list)
        return {
            "job_key": job_key,
            "requests": requests,
            "count_returned": len(requests),
        }

    @server.tool(description="Count pending or running jobs for a Scrapy Cloud project")
    async def scrapy_cloud_count_jobs(
        project_id: int,
        spider: str | None = None,
        state: str | None = None,
        has_tag: list[str] | None = None,
        lacks_tag: list[str] | None = None,
    ) -> dict[str, Any]:
        def _count():
            project = client.get_project(project_id)
            kwargs: dict[str, Any] = {}
            if spider is not None:
                kwargs["spider"] = spider
            if state is not None:
                kwargs["state"] = state
            if has_tag is not None:
                kwargs["has_tag"] = has_tag
            if lacks_tag is not None:
                kwargs["lacks_tag"] = lacks_tag
            return project.jobs.count(**kwargs)

        count = await asyncio.to_thread(_count)
        return {
            "project_id": project_id,
            "count": count,
        }

    @server.tool(description="Get activity events for a Scrapy Cloud project")
    async def scrapy_cloud_get_activity(
        project_id: int,
        count: int | None = None,
    ) -> dict[str, Any]:
        def _get():
            kwargs: dict[str, Any] = {}
            if count is not None:
                kwargs["count"] = count
            return list(client.get_project(project_id).activity.iter(**kwargs))

        events = await asyncio.to_thread(_get)
        return {
            "project_id": project_id,
            "events": events,
            "count_returned": len(events),
        }

    @server.tool(description="List spiders in a Scrapy Cloud project")
    async def scrapy_cloud_list_spiders(project_id: int) -> dict[str, Any]:
        def _list():
            return client.get_project(project_id).spiders.list()

        spiders = await asyncio.to_thread(_list)
        return {
            "project_id": project_id,
            "spiders": spiders,
            "count_returned": len(spiders),
        }
