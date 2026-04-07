"""Retry policy helpers for Zyte API requests."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from zyte_mcp.errors import ZyteAPIError, is_retryable_error

T = TypeVar("T")


def _compute_delay(attempt: int, *, rate_limit: bool) -> float:
    if rate_limit:
        return min(30.0 + (attempt * 5.0), 60.0)
    return min(2.0 * attempt, 10.0)


async def retry_zyte_call(
    operation: Callable[[], Awaitable[T]],
    *,
    rate_limit_max_retries: int,
    download_error_max_retries: int,
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except ZyteAPIError as error:
            if not is_retryable_error(error.status_code, error.error_type):
                raise

            rate_limit = error.status_code in {429, 503}
            max_retries = rate_limit_max_retries if rate_limit else download_error_max_retries
            if attempt >= max_retries:
                raise

            attempt += 1
            await asyncio.sleep(_compute_delay(attempt, rate_limit=rate_limit))
