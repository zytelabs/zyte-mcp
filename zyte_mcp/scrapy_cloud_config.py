"""Configuration for Scrapy Cloud MCP support."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapyCloudSettings:
    api_key: str
    app_base_url: str = "https://app.zyte.com/api"
    storage_base_url: str = "https://storage.zyte.com"
    jobq_base_url: str = "https://jobq.zyte.com"
    request_timeout_seconds: float = 120.0


def get_scrapy_cloud_settings() -> ScrapyCloudSettings:
    api_key = os.getenv("SCRAPY_CLOUD_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SCRAPY_CLOUD_API_KEY is required")
    return ScrapyCloudSettings(api_key=api_key)


def get_scrapy_cloud_settings_optional() -> ScrapyCloudSettings | None:
    api_key = os.getenv("SCRAPY_CLOUD_API_KEY", "").strip()
    if not api_key:
        return None
    return ScrapyCloudSettings(api_key=api_key)
