"""Scrapy Cloud storage read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from zyte_mcp.scrapy_cloud_client import ScrapyCloudClient
from zyte_mcp.scrapy_cloud_models import (
    ScrapyCloudActivityProjectsOptions,
    ScrapyCloudItemsListOptions,
    ScrapyCloudJobQCountFilters,
    ScrapyCloudJobQListFilters,
    ScrapyCloudRequestsListOptions,
    ScrapyCloudStorageQueryOptions,
)


def _coerce_list_result(result: Any) -> list[Any]:
    if isinstance(result, list):
        return result
    if result is None:
        return []
    return [result]


def register_scrapy_cloud_storage_tools(server: FastMCP, client: ScrapyCloudClient) -> None:
    @server.tool(description="Get Scrapy Cloud job metadata")
    async def scrapy_cloud_get_job_metadata(project_id: int, spider_id: int, job_id: int) -> dict[str, Any]:
        raw = await client.get_job_metadata(project_id, spider_id, job_id)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "metadata": raw,
            "raw": raw,
        }

    @server.tool(description="Get one Scrapy Cloud job metadata field")
    async def scrapy_cloud_get_job_metadata_field(
        project_id: int,
        spider_id: int,
        job_id: int,
        field_name: str,
    ) -> dict[str, Any]:
        raw = await client.get_job_metadata(project_id, spider_id, job_id, field_name=field_name)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "field_name": field_name,
            "value": raw,
            "raw": raw,
        }

    @server.tool(description="List Scrapy Cloud stored items")
    async def scrapy_cloud_list_items(
        project_id: int,
        spider_id: int,
        job_id: int,
        options: ScrapyCloudItemsListOptions | None = None,
    ) -> dict[str, Any]:
        params = options.model_dump(exclude_none=True) if options else None
        raw = await client.list_items(project_id, spider_id, job_id, params=params)
        items = _coerce_list_result(raw)
        return {
            "items": items,
            "count_returned": len(items),
            "raw": raw,
        }

    @server.tool(description="Get a single Scrapy Cloud item or field")
    async def scrapy_cloud_get_item(
        project_id: int,
        spider_id: int,
        job_id: int,
        item_no: int,
        field_name: str | None = None,
    ) -> dict[str, Any]:
        raw = await client.list_items(project_id, spider_id, job_id, item_no=item_no, field_name=field_name)
        return {
            "item_no": item_no,
            "field_name": field_name,
            "value": raw,
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud item stats for a job")
    async def scrapy_cloud_get_item_stats(project_id: int, spider_id: int, job_id: int, all_fields: bool = False) -> dict[str, Any]:
        raw = await client.get_item_stats(project_id, spider_id, job_id, all_fields=all_fields)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "stats": raw,
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud logs for a job")
    async def scrapy_cloud_get_logs(
        project_id: int,
        spider_id: int,
        job_id: int,
        options: ScrapyCloudStorageQueryOptions | None = None,
    ) -> dict[str, Any]:
        params = options.model_dump(exclude_none=True) if options else None
        raw = await client.get_logs(project_id, spider_id, job_id, params=params)
        logs = _coerce_list_result(raw)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "logs": logs,
            "count_returned": len(logs),
            "raw": raw,
        }

    @server.tool(description="List Scrapy Cloud request records for a job")
    async def scrapy_cloud_list_requests(
        project_id: int,
        spider_id: int,
        job_id: int,
        options: ScrapyCloudRequestsListOptions | None = None,
    ) -> dict[str, Any]:
        params = options.model_dump(exclude_none=True) if options else None
        raw = await client.list_requests(project_id, spider_id, job_id, params=params)
        requests = _coerce_list_result(raw)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "requests": requests,
            "count_returned": len(requests),
            "raw": raw,
        }

    @server.tool(description="Get a single Scrapy Cloud request record")
    async def scrapy_cloud_get_request(project_id: int, spider_id: int, job_id: int, request_no: int) -> dict[str, Any]:
        raw = await client.list_requests(project_id, spider_id, job_id, request_no=request_no)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "request_no": request_no,
            "value": raw,
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud request stats for a job")
    async def scrapy_cloud_get_request_stats(project_id: int, spider_id: int, job_id: int) -> dict[str, Any]:
        raw = await client.get_request_stats(project_id, spider_id, job_id)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "stats": raw,
            "raw": raw,
        }

    @server.tool(description="Count Scrapy Cloud JobQ entries for a project")
    async def scrapy_cloud_jobq_count(project_id: int, filters: ScrapyCloudJobQCountFilters | None = None) -> dict[str, Any]:
        params = filters.model_dump(exclude_none=True) if filters else None
        count = await client.jobq_count(project_id, params=params)
        return {
            "project_id": project_id,
            "count": count,
        }

    @server.tool(description="List Scrapy Cloud JobQ entries for a project")
    async def scrapy_cloud_jobq_list(project_id: int, filters: ScrapyCloudJobQListFilters | None = None) -> dict[str, Any]:
        params = filters.model_dump(exclude_none=True) if filters else None
        raw = await client.jobq_list(project_id, params=params)
        return {
            "project_id": project_id,
            "jobs": raw,
            "count_returned": len(raw),
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud activity events for one project")
    async def scrapy_cloud_get_activity(project_id: int, count: int | None = None) -> dict[str, Any]:
        params = {"count": count} if count is not None else None
        raw = await client.get_activity(project_id, params=params)
        events = _coerce_list_result(raw)
        return {
            "project_id": project_id,
            "events": events,
            "count_returned": len(events),
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud activity events across projects")
    async def scrapy_cloud_get_projects_activity(options: ScrapyCloudActivityProjectsOptions) -> dict[str, Any]:
        params: dict[str, Any] = {"p": options.project_ids}
        if options.count is not None:
            params["count"] = options.count
        if options.per_project_count is not None:
            params["pcount"] = options.per_project_count
        if options.meta is not None:
            params["meta"] = options.meta

        raw = await client.get_projects_activity(params=params)
        events = _coerce_list_result(raw)
        return {
            "project_ids": options.project_ids,
            "events": events,
            "count_returned": len(events),
            "raw": raw,
        }

    @server.tool(description="List Scrapy Cloud comments for a job")
    async def scrapy_cloud_list_comments(project_id: int, spider_id: int, job_id: int) -> dict[str, Any]:
        raw = await client.list_comments(project_id, spider_id, job_id)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "comments": raw,
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud comment stats for a project")
    async def scrapy_cloud_get_comment_stats(project_id: int) -> dict[str, Any]:
        raw = await client.get_comments_stats(project_id)
        return {
            "project_id": project_id,
            "stats": raw,
            "raw": raw,
        }

    @server.tool(description="Get Scrapy Cloud comments for one item or item field")
    async def scrapy_cloud_get_item_comments(
        project_id: int,
        spider_id: int,
        job_id: int,
        item_no: int,
        field_name: str | None = None,
    ) -> dict[str, Any]:
        raw = await client.get_item_comments(project_id, spider_id, job_id, item_no, field_name=field_name)
        return {
            "job_id": f"{project_id}/{spider_id}/{job_id}",
            "item_no": item_no,
            "field_name": field_name,
            "comments": raw,
            "count_returned": len(raw),
            "raw": raw,
        }
