"""
Fetch page content via the Zyte API using pageContent extraction.

Returns the itemMain text and headline from the pageContent response.
Uses the shared ZyteClient (with auth, retry logic, etc.) instead of raw httpx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zyte_mcp.client import ZyteClient


class FetchError(Exception):
    """Raised when a URL cannot be fetched or has no product content."""


@dataclass
class FetchResult:
    url: str
    item_main: str
    headline: str


async def fetch(url: str, client: ZyteClient) -> FetchResult:
    """Fetch *url* via Zyte pageContent and return item text."""
    payload: dict[str, Any] = {
        "url": url,
        "httpResponseBody": True,
        "pageContent": True,
        "pageContentOptions": {"extractFrom": "httpResponseBody"},
    }

    data = await client.extract(payload)

    page_content = data.get("pageContent") or {}
    item_main = page_content.get("itemMain") or ""
    headline = page_content.get("headline") or ""

    if not item_main:
        raise FetchError(
            f"Zyte API returned no pageContent.itemMain for {url}. "
            "The page may not be a product page."
        )

    return FetchResult(url=url, item_main=item_main, headline=headline)
