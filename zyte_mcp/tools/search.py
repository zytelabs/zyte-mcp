"""Zyte Search API MCP tool."""

from __future__ import annotations

import re
from typing import Any

from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.models import SearchQueryParameters

_ENGINE_SPECIFIC_FIELDS = {"gl", "hl", "cr", "lr", "safe", "nfpr", "uule"}


def _build_query_parameters(qp: SearchQueryParameters) -> dict[str, Any]:
    """Serialise a SearchQueryParameters instance into the API payload dict.

    Automatically selects ``"engineSpecific"`` style when any Google-native
    field is populated; falls back to ``"generic"`` otherwise.
    """
    engine_specific_values = {
        field: getattr(qp, field)
        for field in _ENGINE_SPECIFIC_FIELDS
        if getattr(qp, field) is not None
    }

    if engine_specific_values:
        return {"style": "engineSpecific", **engine_specific_values}

    generic_values: dict[str, Any] = {}
    if qp.geolocation is not None:
        generic_values["geolocation"] = qp.geolocation
    if qp.locale is not None:
        generic_values["locale"] = qp.locale

    return {"style": "generic", **generic_values} if generic_values else {}


def _parse_ai_overview(html: str) -> dict[str, Any] | None:
    """Extract a structured AI overview from a browser-rendered Google SERP.

    Returns a dict with ``text`` and ``sources``, or ``None`` if no AI overview
    is present in the page.

    Google renders the AI overview into a ``<div class="pWvJNd">`` SFC root
    that sits inside the ``heWuVc`` container block.  Source citations live in
    ``<span class="WBgIic …">`` chips whose first ``<a href="…">`` child carries
    the canonical source URL.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Confirm the AI overview heading is present
    heading = soup.find(attrs={"jsname": "cUzNTd"})
    if not heading:
        return None

    # The SFC root div holds the rendered text and source chips
    sfc_root = soup.find("div", class_="pWvJNd")
    if not sfc_root:
        return None

    # --- text ---
    # Strip source-chip spans before extracting prose so they don't bleed in
    for chip in sfc_root.find_all("span", class_="WBgIic"):
        chip.decompose()

    text = sfc_root.get_text(separator=" ", strip=True)
    # Collapse runs of whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()

    if not text:
        return None

    # --- sources ---
    # Re-parse to get the chips back (decompose mutated the tree)
    soup2 = BeautifulSoup(html, "html.parser")
    sfc_root2 = soup2.find("div", class_="pWvJNd")
    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    if sfc_root2:
        for chip in sfc_root2.find_all("span", class_="WBgIic"):
            a = chip.find("a", href=True)
            if not a:
                continue
            url = a["href"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # Chip text is the domain/subreddit label, e.g. "Coursera+2"
            label = re.sub(r"\+\d+$", "", chip.get_text(strip=True)).strip()
            sources.append({"label": label, "url": url})

    return {"text": text, "sources": sources}


def register_search_tools(server: FastMCP, client: ZyteClient) -> None:
    @server.tool(
        description=(
            "Search the web using Zyte's Search API. "
            "Returns structured organic results (rank, title, url, snippet) and/or raw HTML. "
            "Set include_ai_overview=True to trigger full browser rendering and parse Google's "
            "AI Overview into structured text + source citations when one is available. "
            "Supports geo-targeting and locale control via query_parameters. "
            "max_results must be a multiple of 10 between 10 and 100."
        )
    )
    async def search(
        query: str,
        domain: str = "google.com",
        max_results: int = 10,
        include_organic: bool = True,
        include_html: bool = False,
        include_ai_overview: bool = False,
        query_parameters: SearchQueryParameters | None = None,
    ) -> dict[str, Any]:
        include: list[str] = []
        if include_organic:
            include.append("organic")
        # aiOverview triggers browser rendering; the block appears in the html field
        if include_ai_overview:
            include.append("aiOverview")
            include.append("html")
        elif include_html:
            include.append("html")
        if not include:
            include = ["organic"]

        payload: dict[str, Any] = {
            "domain": domain,
            "query": query,
            "include": include,
            "maxResults": max_results,
        }

        if query_parameters is not None:
            qp_dict = _build_query_parameters(query_parameters)
            if qp_dict:
                payload["queryParameters"] = qp_dict

        raw = await client.search(payload)

        result: dict[str, Any] = {
            "url": raw.get("url"),
            "fetched_at": raw.get("fetchedAt"),
            "meta": raw.get("meta"),
            "organic_results": raw.get("organicResults"),
            "total_organic_results": len(raw.get("organicResults") or []),
        }

        html = raw.get("html")
        if include_html:
            result["html"] = html
        if include_ai_overview:
            result["ai_overview"] = _parse_ai_overview(html) if html else None

        return result
