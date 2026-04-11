"""Configuration for Scrapy Cloud MCP support."""

from __future__ import annotations

import os

from scrapinghub import ScrapinghubClient


def _get_scrapy_cloud_api_key() -> str:
    return (
        os.getenv("SCRAPY_CLOUD_API_KEY", "").strip()
        or os.getenv("SHUB_APIKEY", "").strip()
    )


def get_scrapy_cloud_client() -> ScrapinghubClient:
    api_key = _get_scrapy_cloud_api_key()
    if not api_key:
        raise RuntimeError("SCRAPY_CLOUD_API_KEY (or SHUB_APIKEY) is required")
    return ScrapinghubClient(api_key)


def get_scrapy_cloud_client_optional() -> ScrapinghubClient | None:
    api_key = _get_scrapy_cloud_api_key()
    if not api_key:
        return None
    return ScrapinghubClient(api_key)
