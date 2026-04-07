"""Scrapy Cloud jobs tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from zyte_mcp.scrapy_cloud_client import ScrapyCloudClient
from zyte_mcp.scrapy_cloud_models import (
    ScrapyCloudJobsListFilters,
    ScrapyCloudRunJobInput,
    ScrapyCloudTagUpdateInput,
)


def register_scrapy_cloud_jobs_tools(server: FastMCP, client: ScrapyCloudClient) -> None:
    @server.tool(description="Run a Scrapy Cloud spider job")
    async def scrapy_cloud_run_spider(project_id: int, job: ScrapyCloudRunJobInput) -> dict[str, Any]:
        raw = await client.run_job(project_id, job.model_dump(exclude_none=True))
        return {
            "status": raw.get("status"),
            "job_id": raw.get("jobid"),
            "raw": raw,
        }

    @server.tool(description="List Scrapy Cloud jobs")
    async def scrapy_cloud_list_jobs(project_id: int, filters: ScrapyCloudJobsListFilters | None = None) -> dict[str, Any]:
        params = {"project": project_id}
        if filters:
            params.update(filters.model_dump(exclude_none=True))
        raw = await client.list_jobs(params)
        return {
            "count": raw.get("count"),
            "total": raw.get("total"),
            "jobs": raw.get("jobs", []),
            "raw": raw,
        }

    @server.tool(description="Stop a running Scrapy Cloud job")
    async def scrapy_cloud_stop_job(project_id: int, job_id: str) -> dict[str, Any]:
        raw = await client.stop_job(project_id, job_id)
        return {
            "status": raw.get("status"),
            "job_id": job_id,
            "raw": raw,
        }

    @server.tool(description="Update Scrapy Cloud job tags")
    async def scrapy_cloud_update_job_tags(
        project_id: int,
        job_id: str,
        update: ScrapyCloudTagUpdateInput,
    ) -> dict[str, Any]:
        raw = await client.update_job_tags(project_id, job_id, update.model_dump(exclude_none=True))
        return {
            "status": raw.get("status"),
            "job_id": job_id,
            "raw": raw,
        }
