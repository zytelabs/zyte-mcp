![Zyte MCP community edition](zyte-mcp-banner.png)

# zyte-mcp

> **Disclaimer:** This is not an official Zyte product. It is an independent, community-built MCP server. APIs, tool behaviour, and configuration may change without notice.

Task-focused MCP server for the Zyte API and Scrapy Cloud, designed to be used with AI coding assistants such as Claude.

## Requirements

- Python 3.13+
- `ZYTE_API_KEY` — required for all Zyte API tools
- `SCRAPY_CLOUD_API_KEY` (or `SHUB_APIKEY`) — required for Scrapy Cloud tools only

## Install

```bash
uv sync --extra dev
```

## Run

```bash
ZYTE_API_KEY=your-key uv run zyte-mcp
```

The server communicates over `stdio`.

To enable Scrapy Cloud tools as well:

```bash
ZYTE_API_KEY=your-key SCRAPY_CLOUD_API_KEY=your-scrapy-cloud-key uv run zyte-mcp
```

`SHUB_APIKEY` is accepted as an alias for `SCRAPY_CLOUD_API_KEY`.

## Claude Desktop

Claude Desktop on macOS reads MCP server config from:

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Minimal config (Zyte API tools only):

```json
{
  "mcpServers": {
    "zyte": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/zyte-mcp",
        "zyte-mcp"
      ],
      "env": {
        "ZYTE_API_KEY": "your-zyte-api-key"
      }
    }
  }
}
```

Add `SCRAPY_CLOUD_API_KEY` to the `env` block to also enable the Scrapy Cloud tools.

If Claude Desktop cannot find `uv`, replace `"uv"` with the absolute path returned by `which uv`, then fully restart Claude Desktop.

## Tools

### Zyte API — HTTP

**`fetch_http`**  
Fetch a URL using Zyte HTTP mode (no browser rendering).

- Returns decoded text when possible; raw body available as `body_base64`
- Supports custom headers, cookies, POST body, geolocation, and residential IPs
- Use for static HTML, JSON APIs, sitemaps, and any page that does not require JavaScript

**`render_page`**  
Render a page using a real browser via Zyte.

- Returns full browser HTML after JavaScript execution
- Supports browser actions: `click`, `type`, `scroll_bottom`, `scroll_to`, `wait_for_selector`, `wait_for_timeout`, `select`, `hover`, `key_press`, `evaluate`
- Can include content from iframes via `include_iframes`
- Use when a page requires JavaScript or user interaction before content is visible

**`screenshot_page`**  
Capture a screenshot of a page using Zyte browser mode.

- Returns a JPEG or PNG image
- Supports `full_page` capture and the same browser action set as `render_page`
- Useful for visually verifying a page or debugging rendering issues

### Zyte API — Search

**`search`**  
Search the web using Zyte's Search API (`POST /v1/search`).

- `query` — search keywords
- `domain` — search engine domain (default: `google.com`)
- `max_results` — number of organic results to return; must be a multiple of 10 between 10 and 100 (default: `10`)
- `include_organic` — return parsed organic results with `rank`, `title`, `url`, `snippet`, `displayed_url` (default: `true`)
- `include_html` — return the raw SERP HTML; can be combined with `include_ai_overview` at no extra API cost since browser HTML is fetched either way (default: `false`)
- `include_ai_overview` — trigger full browser rendering and parse Google's AI Overview into structured `{ text, sources[] }` when one is available for the query (default: `false`)
- `query_parameters` — optional geo-targeting and locale control:
  - Generic (portable): `geolocation` (e.g. `"US"`), `locale` (e.g. `"en-US"`)
  - Engine-specific (Google): `gl`, `hl`, `cr`, `lr`, `safe`, `nfpr`, `uule` — style is auto-detected from which fields are set

### Zyte API — Extraction

All extraction tools call Zyte's AI-powered automatic extraction. They share a common set of options: `extract_from`, `geolocation`, `ip_type`, `session_id`, `request_cookies`, `response_cookies`, and `custom_attributes`.

**`extract_product`**  
Extract structured product data (name, price, SKU, images, description, availability, etc.) from a product detail page.

**`extract_product_list`**  
Extract a list of product summaries from a category or search results page.

**`extract_article`**  
Extract structured article data (headline, body text, author, date, etc.) from a news or blog page.

**`extract_page_content`**  
Extract the main readable content from any page when a more specific type does not apply.

### Scrapy Cloud — Deploy

**`scrapy_cloud_deploy`**  
Deploy a local Scrapy project to Scrapy Cloud.

- Requires `shub` to be available; install it with `uv add shub` inside the project, or globally with `pip install shub`
- When a `.venv` is present in the project directory, invokes `shub` via `uv run shub` automatically
- Runs preflight checks before deploying:
  - Verifies `shub` is callable
  - Verifies `scrapy.cfg` is present at `project_path`
  - Verifies a target project is known (`scrapinghub.yml` exists, or `project_id` is supplied)
- When `project_id` is supplied and no `scrapinghub.yml` exists yet, the tool creates both files automatically:
  - **`requirements.txt`** — built from `[project].dependencies` in `pyproject.toml`, with `scrapy` itself excluded (the cloud stack provides it)
  - **`scrapinghub.yml`** — minimal config with the project ID, the correct Scrapy stack version (`stack: scrapy:X.Y`), and a pointer to `requirements.txt`
- On failure, any scrapy version mismatch detected in the output is surfaced as `scrapy_version_hint`
- Returns `success`, `project_id`, `version`, `stdout`, `stderr`

### Scrapy Cloud — Jobs

**`scrapy_cloud_run_spider`**  
Start a spider job on Scrapy Cloud. Accepts `project_id`, `spider` name, optional `job_args`, `job_settings`, `priority`, `units`, and `add_tag`.

**`scrapy_cloud_list_jobs`**  
List jobs for a project. Filter by `spider`, `state` (`pending`, `running`, `finished`), `has_tag`, `lacks_tag`, and `count`.

**`scrapy_cloud_cancel_job`**  
Cancel a running or pending job. Accepts `job_key` in `project_id/spider_id/job_id` format.

**`scrapy_cloud_update_job_tags`**  
Add or remove tags on a job. Pass lists of tag strings to `add` and/or `remove`.

**`scrapy_cloud_count_jobs`**  
Count pending or running jobs for a project, optionally filtered by spider name or tags.

**`scrapy_cloud_get_activity`**  
Get recent activity events for a project (deploys, job state changes, etc.).

**`scrapy_cloud_list_spiders`**  
List all spiders deployed to a Scrapy Cloud project.

### Scrapy Cloud — Job Data

**`scrapy_cloud_get_job_metadata`**  
Return all metadata fields for a job (spider name, state, timestamps, item count, error count, etc.).

**`scrapy_cloud_get_job_metadata_field`**  
Return a single named metadata field for a job. More efficient than fetching all metadata when only one value is needed.

**`scrapy_cloud_list_items`**  
Return scraped items from a finished job. Supports `start` offset and `count` limit for pagination.

**`scrapy_cloud_get_logs`**  
Return log entries for a job. Supports `count` to limit the number of lines returned.

**`scrapy_cloud_list_requests`**  
Return HTTP request records logged during a job. Supports `start` and `count` for pagination.

## Work in progress

**`infer_product_schema`** — a tool that infers a typed product data schema from one or more product page URLs (fetching via Zyte API, extracting fields with Claude, and generating an `@attrs.define` class + JSON Schema) exists in the codebase but is not yet exposed to tool users. It is disabled pending further testing and refinement.

## Caveats

- `ip_type="residential"` may cost more and requires Zyte KYC approval
- Geolocation choices may affect both cost and success rate
- `session_id` is client-managed; this server does not create or persist sessions
- `custom_attributes` require a standard extraction type and are not supported with `serp`
- Browser tools only support `referer` as an initial request header
- Scrapy Cloud uses a separate API key from Zyte API
- Scrapy Cloud mutation operations are intentionally limited to running jobs, cancelling jobs, and updating tags

## Test

```bash
uv run pytest
```
