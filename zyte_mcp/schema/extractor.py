"""
Extract structured product fields from pageContent.itemMain text using Claude.

Sends the raw itemMain text to Claude and asks it to return a flat JSON dict
with all product fields it can find on the page.
"""

from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from zyte_mcp.schema.fetcher import FetchResult

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """\
You are a product data extraction assistant. Given the text content of a product page, \
extract ALL product fields and return them as a single flat JSON object.

Always extract these core fields if present:
- name (str): product name/title
- sku (str): SKU, model number, or product ID
- brand (str): brand or manufacturer
- category (str): product category
- price (number): current/sale price (numeric only, no currency symbol)
- currency (str): currency code (e.g. USD, EUR, GBP)
- regular_price (number): original/regular price if a sale price is shown, else null
- availability (str): stock status (e.g. "In stock", "Out of stock")
- description (str): product description
- weight (str): weight with units
- dimensions (str): dimensions with units
- gtin (str): GTIN, EAN, UPC, or barcode
- rating_value (number): numeric rating value
- review_count (number): number of reviews (integer)
- tags (array of strings): product tags or keywords

In addition, extract ALL other product-specific fields from the page — every specification, \
attribute, feature, or technical detail present in the text. Use snake_case field names \
(e.g. cpu_cores, base_clock, l3_cache, tdp, socket, memory_support, launch_date, os_support). \
Do not skip any field that has a concrete value — include everything.

Rules:
- Return ONLY a valid JSON object, no markdown, no explanation.
- Omit fields entirely if not present (do not include null values).
- price, regular_price, rating_value, review_count must be numbers (not strings).
- tags must be an array of strings.
- Numeric spec values with units should be kept as strings (e.g. "5.0 GHz", "120 W", "96 MB").
- Multi-value specs (e.g. OS support listing multiple OSes) should be arrays of strings.
- Do not invent values; only extract what is explicitly stated in the text.
"""


class ExtractError(Exception):
    """Raised when extraction fails."""


async def extract_page(
    result: FetchResult,
    anthropic_client: AsyncAnthropic,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """
    Use Claude to extract product fields from a FetchResult's itemMain text.

    Returns a flat dict[str, object] with extracted fields.
    Null/missing values are omitted from the returned dict.
    """
    user_content = f"Extract product fields from this product page text:\n\n{result.item_main}"

    message = await anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw_text = "\n".join(inner).strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ExtractError(
            f"Claude returned invalid JSON for {result.url}: {exc}\nRaw: {raw_text[:300]}"
        ) from exc

    if not isinstance(data, dict):
        raise ExtractError(
            f"Claude returned non-dict JSON for {result.url}: {type(data).__name__}"
        )

    # Filter out null values, empty strings, and empty lists
    fields: dict[str, object] = {}
    for key_name, value in data.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        fields[key_name] = value

    return fields
