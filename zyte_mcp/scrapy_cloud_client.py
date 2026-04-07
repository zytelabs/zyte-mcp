"""Async client for Scrapy Cloud HTTP and Storage APIs."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from zyte_mcp.errors import ZyteAPIError
from zyte_mcp.scrapy_cloud_config import ScrapyCloudSettings


class ScrapyCloudAPIError(ZyteAPIError):
    pass


class ScrapyCloudClient:
    def __init__(self, settings: ScrapyCloudSettings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = client or httpx.AsyncClient(timeout=settings.request_timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def run_job(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        form: dict[str, Any] = {"project": str(project_id)}
        for key, value in payload.items():
            if key == "spider_args" and isinstance(value, Mapping):
                form.update(value)
            else:
                form[key] = value
        return await self._request_json("POST", f"{self.settings.app_base_url}/run.json", data=form)

    async def list_jobs(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("GET", f"{self.settings.app_base_url}/jobs/list.json", params=params)

    async def stop_job(self, project_id: int, job_id: str) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self.settings.app_base_url}/jobs/stop.json",
            data={"project": str(project_id), "job": job_id},
        )

    async def update_job_tags(self, project_id: int, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"{self.settings.app_base_url}/jobs/update.json",
            data={"project": str(project_id), "job": job_id, **payload},
        )

    async def list_comments(self, project_id: int, spider_id: int, job_id: int) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            f"{self.settings.app_base_url}/comments/{project_id}/{spider_id}/{job_id}",
        )

    async def get_comments_stats(self, project_id: int) -> dict[str, Any]:
        return await self._request_json("GET", f"{self.settings.app_base_url}/comments/{project_id}/stats")

    async def get_item_comments(
        self,
        project_id: int,
        spider_id: int,
        job_id: int,
        item_no: int,
        field_name: str | None = None,
    ) -> list[dict[str, Any]]:
        suffix = f"/{field_name}" if field_name else ""
        result = await self._request_mixed(
            "GET",
            f"{self.settings.app_base_url}/comments/{project_id}/{spider_id}/{job_id}/{item_no}{suffix}",
        )
        if isinstance(result, list):
            return result
        if result is None:
            return []
        return [result]

    async def get_job_metadata(self, project_id: int, spider_id: int, job_id: int, field_name: str | None = None) -> Any:
        suffix = f"/{field_name}" if field_name else ""
        return await self._request_mixed(
            "GET",
            f"{self.settings.storage_base_url}/jobs/{project_id}/{spider_id}/{job_id}{suffix}",
        )

    async def list_items(
        self,
        project_id: int,
        spider_id: int | None = None,
        job_id: int | None = None,
        item_no: int | None = None,
        field_name: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = self._storage_url("items", project_id, spider_id, job_id, item_no, field_name)
        return await self._request_mixed("GET", url, params=params)

    async def list_requests(
        self,
        project_id: int,
        spider_id: int | None = None,
        job_id: int | None = None,
        request_no: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = self._storage_url("requests", project_id, spider_id, job_id, request_no)
        return await self._request_mixed("GET", url, params=params)

    async def get_request_stats(self, project_id: int, spider_id: int, job_id: int) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            f"{self.settings.storage_base_url}/requests/{project_id}/{spider_id}/{job_id}/stats",
        )

    async def get_item_stats(self, project_id: int, spider_id: int, job_id: int, all_fields: bool = False) -> dict[str, Any]:
        params = {"all": 1} if all_fields else None
        return await self._request_json(
            "GET",
            f"{self.settings.storage_base_url}/items/{project_id}/{spider_id}/{job_id}/stats",
            params=params,
        )

    async def get_logs(
        self,
        project_id: int,
        spider_id: int,
        job_id: int,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request_mixed(
            "GET",
            f"{self.settings.storage_base_url}/logs/{project_id}/{spider_id}/{job_id}",
            params=params,
        )

    async def get_activity(self, project_id: int, params: dict[str, Any] | None = None) -> Any:
        return await self._request_mixed("GET", f"{self.settings.storage_base_url}/activity/{project_id}", params=params)

    async def get_projects_activity(self, params: dict[str, Any] | None = None) -> Any:
        return await self._request_mixed("GET", f"{self.settings.storage_base_url}/activity/projects", params=params)

    async def jobq_count(self, project_id: int, params: dict[str, Any] | None = None) -> int:
        result = await self._request_mixed("GET", f"{self.settings.jobq_base_url}/jobq/{project_id}/count", params=params)
        if isinstance(result, int):
            return result
        if isinstance(result, str):
            return int(result)
        raise ValueError("Unexpected JobQ count response")

    async def jobq_list(self, project_id: int, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = await self._request_mixed("GET", f"{self.settings.jobq_base_url}/jobq/{project_id}/list", params=params)
        if isinstance(result, list):
            return result
        if result is None:
            return []
        return [result]

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.request(
            method,
            url,
            auth=(self.settings.api_key, ""),
            params=self._normalize_params(params),
            data=self._normalize_form_data(data),
            headers={"Accept": "application/json"},
        )
        return await self._handle_json_response(response)

    async def _request_mixed(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.request(
            method,
            url,
            auth=(self.settings.api_key, ""),
            params=self._normalize_params(params),
            headers={"Accept": "application/json, application/x-jsonlines"},
        )
        return await self._handle_mixed_response(response)

    async def _handle_json_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise self._build_error(response)
        if not response.content:
            return {}
        return response.json()

    async def _handle_mixed_response(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            raise self._build_error(response)
        text = response.text.strip()
        if not text:
            return []

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) == 1:
            try:
                return json.loads(lines[0])
            except json.JSONDecodeError:
                return text

        parsed: list[Any] = []
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                parsed.append(line)
        return parsed

    def _build_error(self, response: httpx.Response) -> ScrapyCloudAPIError:
        payload = None
        detail = response.text or "Request failed"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("message") or payload.get("error") or payload.get("status") or detail
        except json.JSONDecodeError:
            payload = None

        return ScrapyCloudAPIError(
            status_code=response.status_code,
            error_type=None,
            detail=detail,
            payload=payload if isinstance(payload, dict) else None,
        )

    @staticmethod
    def _normalize_params(params: dict[str, Any] | None) -> dict[str, Any] | tuple[tuple[str, str], ...] | None:
        if not params:
            return None

        pairs: list[tuple[str, str]] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    pairs.append((key, str(item)))
            elif isinstance(value, bool):
                pairs.append((key, "1" if value else "0"))
            else:
                pairs.append((key, str(value)))
        return tuple(pairs)

    @staticmethod
    def _normalize_form_data(
        data: Mapping[str, Any] | None,
    ) -> dict[str, str] | None:
        if not data:
            return None

        normalized: dict[str, str] = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value)
            elif isinstance(value, bool):
                normalized[key] = "1" if value else "0"
            else:
                normalized[key] = str(value)
        return normalized

    def _storage_url(
        self,
        prefix: str,
        project_id: int,
        spider_id: int | None = None,
        job_id: int | None = None,
        entity_no: int | None = None,
        field_name: str | None = None,
    ) -> str:
        parts = [prefix, str(project_id)]
        if spider_id is not None:
            parts.append(str(spider_id))
        if job_id is not None:
            parts.append(str(job_id))
        if entity_no is not None:
            parts.append(str(entity_no))
        if field_name is not None:
            parts.append(field_name)
        return f"{self.settings.storage_base_url}/{'/'.join(parts)}"
