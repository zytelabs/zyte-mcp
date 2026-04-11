"""Scrapy Cloud jobs tools."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP
from scrapinghub import ScrapinghubClient


def register_scrapy_cloud_jobs_tools(server: FastMCP, client: ScrapinghubClient) -> None:
    @server.tool(description="Run a Scrapy Cloud spider job")
    async def scrapy_cloud_run_spider(
        project_id: int,
        spider: str,
        job_args: dict[str, Any] | None = None,
        job_settings: dict[str, Any] | None = None,
        units: int | None = None,
        priority: int | None = None,
        add_tag: list[str] | None = None,
    ) -> dict[str, Any]:
        def _run():
            project = client.get_project(project_id)
            kwargs: dict[str, Any] = {}
            if job_args:
                kwargs["job_args"] = job_args
            if job_settings:
                kwargs["job_settings"] = job_settings
            if units is not None:
                kwargs["units"] = units
            if priority is not None:
                kwargs["priority"] = priority
            if add_tag:
                kwargs["add_tag"] = add_tag
            job = project.jobs.run(spider, **kwargs)
            return job.key

        job_key = await asyncio.to_thread(_run)
        return {
            "job_key": job_key,
        }

    @server.tool(description="List Scrapy Cloud jobs for a project")
    async def scrapy_cloud_list_jobs(
        project_id: int,
        spider: str | None = None,
        state: str | None = None,
        has_tag: list[str] | None = None,
        lacks_tag: list[str] | None = None,
        count: int | None = None,
    ) -> dict[str, Any]:
        def _list():
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
            if count is not None:
                kwargs["count"] = count
            return list(project.jobs.iter(**kwargs))

        jobs = await asyncio.to_thread(_list)
        return {
            "jobs": jobs,
            "count_returned": len(jobs),
        }

    @server.tool(description="Cancel a running or pending Scrapy Cloud job")
    async def scrapy_cloud_cancel_job(job_key: str) -> dict[str, Any]:
        def _cancel():
            client.get_job(job_key).cancel()

        await asyncio.to_thread(_cancel)
        return {
            "job_key": job_key,
            "cancelled": True,
        }

    @server.tool(description="Update tags on a Scrapy Cloud job")
    async def scrapy_cloud_update_job_tags(
        job_key: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> dict[str, Any]:
        if not add and not remove:
            raise ValueError("At least one of 'add' or 'remove' must be provided")

        def _update():
            kwargs: dict[str, Any] = {}
            if add:
                kwargs["add"] = add
            if remove:
                kwargs["remove"] = remove
            client.get_job(job_key).update_tags(**kwargs)

        await asyncio.to_thread(_update)
        return {
            "job_key": job_key,
            "updated": True,
        }
