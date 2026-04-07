"""Configuration for the Zyte MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ZyteSettings:
    api_key: str
    base_url: str = "https://api.zyte.com/v1/extract"
    request_timeout_seconds: float = 120.0
    rate_limit_max_retries: int = 8
    download_error_max_retries: int = 3


def get_settings() -> ZyteSettings:
    api_key = os.getenv("ZYTE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ZYTE_API_KEY is required")
    return ZyteSettings(api_key=api_key)
