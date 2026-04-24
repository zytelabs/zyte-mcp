"""
MCP tool: infer_product_schema

Runs the auto-schema pipeline against one or more product page URLs:
  1. Fetch each URL via Zyte API pageContent extraction.
  2. Use Claude to extract all product fields as JSON.
  3. Merge field dicts across pages (tracking required vs optional).
  4. Infer Python types for each field.
  5. Return the schema + attrs class string + JSON Schema string.

Requires ANTHROPIC_API_KEY to be set in the environment.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urlparse

from anthropic import AsyncAnthropic
from fastmcp import FastMCP

from zyte_mcp.client import ZyteClient
from zyte_mcp.schema import extractor, merger, type_infer
from zyte_mcp.schema.codegen import attrs_, json_schema
from zyte_mcp.schema.fetcher import FetchError, FetchResult, fetch
from zyte_mcp.schema.extractor import ExtractError


def _domain_slug(url: str) -> str:
    """Convert a URL's domain to a snake_case slug, stripping www."""
    host = urlparse(url).hostname or ""
    host = re.sub(r"^www\.", "", host)
    return re.sub(r"[^a-z0-9]+", "_", host.lower()).strip("_")


def _default_class_name(slug: str) -> str:
    """Convert a domain slug to a PascalCase class name, e.g. scan_co_uk → ScanCoUkProduct."""
    parts = [p.capitalize() for p in slug.split("_") if p]
    return "".join(parts) + "Product"


def register_schema_tools(
    server: FastMCP,
    zyte_client: ZyteClient,
    anthropic_client: AsyncAnthropic,
) -> None:
    """Register the infer_product_schema tool on *server*."""

    @server.tool(
        description=(
            "Infer a typed product data schema from one or more product page URLs.\n\n"
            "Fetches each URL via Zyte API pageContent extraction, uses Claude to extract "
            "all product fields as structured JSON, merges the fields across all pages "
            "(marking fields that don't appear on every page as optional), infers Python "
            "types, and returns:\n"
            "  - schema: list of {name, type, optional, example} objects\n"
            "  - codegen.attrs: ready-to-use @attrs.define class source\n"
            "  - codegen.json_schema: JSON Schema Draft 2020-12 document\n"
            "  - items: per-URL extracted field dicts\n\n"
            "All URLs must be from the same domain. At least one URL is required.\n\n"
            "Requires ANTHROPIC_API_KEY to be set in the environment."
        )
    )
    async def infer_product_schema(
        urls: list[str],
        class_name: str | None = None,
        fields: list[str] | None = None,
        anthropic_model: str = "claude-haiku-4-5-20251001",
    ) -> dict[str, Any]:
        """
        Infer a typed product data schema from one or more product page URLs.

        Args:
            urls: One or more product page URLs. All must share the same domain.
            class_name: Override the auto-derived Python class name
                        (default: DomainSlugProduct, e.g. ScanCoUkProduct).
            fields: Whitelist of field names to include in the output.
                    If omitted, all discovered fields are returned.
            anthropic_model: Claude model to use for field extraction.
                             Default: claude-haiku-4-5-20251001.

        Returns:
            dict with keys: domain, class_name, schema, codegen, items.
        """
        if not urls:
            return {"error": "At least one URL is required."}

        # Derive domain metadata from first URL
        slug = _domain_slug(urls[0])
        derived_class_name = class_name or _default_class_name(slug)
        domain = urlparse(urls[0]).hostname or ""

        # Stage 1 + 2: Fetch and extract all URLs in parallel
        async def fetch_and_extract(url: str) -> tuple[str, dict[str, object] | str]:
            """Returns (url, fields_dict) or (url, error_message)."""
            try:
                result: FetchResult = await fetch(url, zyte_client)
            except FetchError as e:
                return url, f"FetchError: {e}"

            try:
                page_fields = await extractor.extract_page(
                    result, anthropic_client, model=anthropic_model
                )
            except ExtractError as e:
                return url, f"ExtractError: {e}"

            return url, page_fields

        results = await asyncio.gather(*[fetch_and_extract(u) for u in urls])

        # Separate successes from errors
        page_items: list[dict[str, Any]] = []
        page_field_dicts: list[dict[str, object]] = []
        errors: list[dict[str, str]] = []

        for url, outcome in results:
            if isinstance(outcome, str):
                errors.append({"url": url, "error": outcome})
            else:
                page_items.append({"url": url, "fields": outcome})
                page_field_dicts.append(outcome)

        if not page_field_dicts:
            return {
                "domain": domain,
                "class_name": derived_class_name,
                "errors": errors,
                "schema": [],
                "codegen": {"attrs": "", "json_schema": "{}"},
                "items": [],
            }

        # Stage 3: Merge
        merged = merger.merge(page_field_dicts)

        # Stage 4: Infer types
        inferred = type_infer.infer(merged, derived_class_name)

        # Apply field whitelist if requested
        if fields:
            field_set = set(fields)
            inferred.fields = [f for f in inferred.fields if f.name in field_set]
            page_items = [
                {"url": item["url"], "fields": {k: v for k, v in item["fields"].items() if k in field_set}}
                for item in page_items
            ]

        # Stage 5: Codegen
        attrs_source = attrs_.render(inferred)
        json_schema_source = json_schema.render(inferred)

        # Build output schema list
        schema_list = [
            {
                "name": f.name,
                "type": type_infer.type_annotation(f),
                "optional": f.optional,
                "example": f.example,
            }
            for f in inferred.fields
        ]

        result_dict: dict[str, Any] = {
            "domain": domain,
            "class_name": derived_class_name,
            "schema": schema_list,
            "codegen": {
                "attrs": attrs_source,
                "json_schema": json_schema_source,
            },
            "items": page_items,
        }

        if errors:
            result_dict["errors"] = errors

        return result_dict
