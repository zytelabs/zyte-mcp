"""Automatic extraction MCP tools backed by Zyte API."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.models import ExtractionOptions, SerpOptions
from zyte_mcp.tools.common import apply_common_options, normalize_response_cookies, normalize_response_headers


def _build_extraction_result(raw: dict[str, Any], field_name: str, url: str) -> dict[str, Any]:
    return {
        "url": raw.get("url", url),
        "status_code": raw.get("statusCode"),
        "data": raw.get(field_name),
        "metadata": (raw.get(field_name) or {}).get("metadata") if isinstance(raw.get(field_name), dict) else None,
        "custom_attributes": raw.get("customAttributes"),
        "response_headers": normalize_response_headers(raw),
        "response_cookies": normalize_response_cookies(raw),
        "raw": raw,
    }


def register_extraction_tools(server: FastMCP, client: ZyteClient) -> None:
    async def run_extraction(url: str, field_name: str, options: ExtractionOptions | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            field_name: True,
        }
        apply_common_options(payload, options)
        raw = await client.extract(payload)
        return _build_extraction_result(raw, field_name, url)

    @server.tool(description="Extract product data from a product detail page")
    async def extract_product(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "product", options)

    @server.tool(description="Extract a list of products from a product listing or category page")
    async def extract_product_list(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "productList", options)

    @server.tool(description="Extract product navigation data (next page link, sub-categories, and product links) from a product listing or category page. Use this to crawl paginated product catalogues.")
    async def extract_product_navigation(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "productNavigation", options)

    @server.tool(description="Extract article data from an article or news page")
    async def extract_article(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "article", options)

    @server.tool(description="Extract a list of articles (with summaries) from an article listing or news index page")
    async def extract_article_list(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "articleList", options)

    @server.tool(description="Extract article navigation data (next page link and article links) from an article listing page. Use this to crawl paginated article archives.")
    async def extract_article_navigation(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "articleNavigation", options)

    @server.tool(description="Extract forum thread data (topic and posts with reactions) from a forum thread page")
    async def extract_forum_thread(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "forumThread", options)

    @server.tool(description="Extract job posting data (title, description, salary, location, hiring organization) from a job listing detail page")
    async def extract_job_posting(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "jobPosting", options)

    @server.tool(description="Extract job posting navigation data (next page link and job links) from a job listing index page. Use this to crawl paginated job boards. Cannot be combined with jobPosting in the same request.")
    async def extract_job_posting_navigation(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "jobPostingNavigation", options)

    @server.tool(description="Extract page content from a page")
    async def extract_page_content(url: str, options: ExtractionOptions | None = None) -> dict[str, Any]:
        return await run_extraction(url, "pageContent", options)

    @server.tool(description="Extract data from a search engine results page (SERP). The URL must be a Google search URL. Only serpOptions and url are accepted; this cannot be combined with other extraction fields. Fetches multiple pages concurrently using the Google 'start' pagination parameter.")
    async def extract_serp(url: str, pages: int = 5, options: SerpOptions | None = None) -> dict[str, Any]:
        opts = options or SerpOptions()
        serp_options: dict[str, Any] = {"extractFrom": opts.extract_from}
        if opts.include_iframes:
            serp_options["includeIframes"] = opts.include_iframes

        def _page_url(base: str, page: int) -> str:
            """Return the Google search URL for the given 1-based page number."""
            parsed = urlparse(base)
            params = parse_qs(parsed.query, keep_blank_values=True)
            if page == 1:
                params.pop("start", None)
            else:
                params["start"] = [str((page - 1) * 10)]
            new_query = urlencode({k: v[0] for k, v in params.items()})
            return urlunparse(parsed._replace(query=new_query))

        async def _fetch_page(page: int) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "url": _page_url(url, page),
                "serp": True,
                "serpOptions": serp_options,
            }
            return await client.extract(payload)

        pages = max(1, pages)
        raws = await asyncio.gather(*[_fetch_page(p) for p in range(1, pages + 1)])

        all_results: list[dict[str, Any]] = []
        for raw in raws:
            serp_data = raw.get("serp") or {}
            all_results.extend(serp_data.get("organicResults") or [])

        first_serp = (raws[0].get("serp") or {}) if raws else {}
        return {
            "url": raws[0].get("url", url) if raws else url,
            "pages_fetched": len(raws),
            "status_codes": [r.get("statusCode") for r in raws],
            "organic_results": all_results,
            "total_organic_results_count": len(all_results),
            "metadata": first_serp.get("metadata"),
            "raw": raws,
        }
