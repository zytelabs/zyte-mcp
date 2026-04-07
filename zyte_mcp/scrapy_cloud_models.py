"""Shared models for Scrapy Cloud MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ScrapyCloudJobsListFilters(BaseModel):
    job: str | None = None
    spider: str | None = None
    state: Literal["pending", "running", "finished", "deleted"] | None = None
    has_tag: str | None = None
    lacks_tag: str | None = None
    count: int | None = Field(default=None, ge=1)
    offset: int | None = Field(default=None, ge=0)


class ScrapyCloudRunJobInput(BaseModel):
    spider: str | None = None
    jobq_id: int | None = None
    priority: int | None = Field(default=None, ge=0, le=4)
    units: int | None = Field(default=None, ge=1, le=6)
    add_tag: str | None = None
    job_settings: dict[str, Any] | None = None
    spider_args: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_spider_or_jobq(self) -> "ScrapyCloudRunJobInput":
        if not self.spider and self.jobq_id is None:
            raise ValueError("Either spider or jobq_id is required")
        return self


class ScrapyCloudTagUpdateInput(BaseModel):
    add_tag: str | None = None
    remove_tag: str | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "ScrapyCloudTagUpdateInput":
        if not self.add_tag and not self.remove_tag:
            raise ValueError("At least one of add_tag or remove_tag is required")
        return self


class ScrapyCloudStorageQueryOptions(BaseModel):
    count: int | None = Field(default=None, ge=1)
    start: str | None = None
    startafter: str | None = None
    index: list[str] | None = None
    meta: list[str] | None = None


class ScrapyCloudItemsListOptions(ScrapyCloudStorageQueryOptions):
    nodata: bool = False


class ScrapyCloudRequestsListOptions(ScrapyCloudStorageQueryOptions):
    nodata: bool = False


class ScrapyCloudJobQCountFilters(BaseModel):
    spider: str | None = None
    state: Literal["pending", "running", "finished", "deleted"] | None = None
    startts: int | None = Field(default=None, ge=0)
    endts: int | None = Field(default=None, ge=0)
    has_tag: list[str] | None = None
    lacks_tag: list[str] | None = None


class ScrapyCloudJobQListFilters(ScrapyCloudJobQCountFilters):
    count: int | None = Field(default=None, ge=1)
    start: int | None = Field(default=None, ge=0)
    stop: str | None = None
    key: list[str] | None = None


class ScrapyCloudActivityProjectsOptions(BaseModel):
    project_ids: list[int]
    count: int | None = Field(default=None, ge=1)
    per_project_count: int | None = Field(default=None, ge=1)
    meta: list[str] | None = None

    @model_validator(mode="after")
    def validate_project_ids(self) -> "ScrapyCloudActivityProjectsOptions":
        if not self.project_ids:
            raise ValueError("At least one project_id is required")
        return self
