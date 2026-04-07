# zyte-mcp

Task-focused MCP server for Zyte API.

## Requirements

- Python 3.13+
- `ZYTE_API_KEY` set in the environment
- `SCRAPY_CLOUD_API_KEY` set in the environment only if you want Scrapy Cloud tools

## Install

```bash
uv sync --extra dev
```

## Run

```bash
ZYTE_API_KEY=your-key uv run zyte-mcp
```

The server runs over `stdio`.

To enable Scrapy Cloud tools as well:

```bash
ZYTE_API_KEY=your-key SCRAPY_CLOUD_API_KEY=your-scrapy-cloud-key uv run zyte-mcp
```

## Claude Desktop

Claude Desktop on macOS reads MCP server config from:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

Ready-to-paste config:

```json
{
  "mcpServers": {
    "zyte": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/john.rooney/Projects/zyte-mcp",
        "zyte-mcp"
      ],
      "env": {
        "ZYTE_API_KEY": "your-zyte-api-key"
      }
    }
  }
}
```

Add `SCRAPY_CLOUD_API_KEY` to the `env` block only if you want the Scrapy Cloud tools to be available.

If Claude Desktop cannot find `uv`, replace `"uv"` with the absolute path from:

```bash
which uv
```

Then fully restart Claude Desktop.

## Tools

- `fetch_http`
- `render_page`
- `screenshot_page`
- `extract_product`
- `extract_product_list`
- `extract_article`
- `extract_page_content`
- `scrapy_cloud_run_spider`
- `scrapy_cloud_list_jobs`
- `scrapy_cloud_stop_job`
- `scrapy_cloud_update_job_tags`
- `scrapy_cloud_get_job_metadata`
- `scrapy_cloud_get_job_metadata_field`
- `scrapy_cloud_list_items`
- `scrapy_cloud_get_item`
- `scrapy_cloud_get_item_stats`
- `scrapy_cloud_get_logs`
- `scrapy_cloud_list_requests`
- `scrapy_cloud_get_request`
- `scrapy_cloud_get_request_stats`
- `scrapy_cloud_jobq_count`
- `scrapy_cloud_jobq_list`
- `scrapy_cloud_get_activity`
- `scrapy_cloud_get_projects_activity`
- `scrapy_cloud_list_comments`
- `scrapy_cloud_get_comment_stats`
- `scrapy_cloud_get_item_comments`

All tools return normalized top-level fields plus the full raw Zyte response under `raw`.

## Tool Notes

`fetch_http`:
- uses Zyte HTTP mode
- decodes text responses when possible
- returns Base64 body as `body_base64`

`render_page`:
- uses Zyte browser mode
- supports a curated browser action set
- can include iframe HTML

`screenshot_page`:
- uses Zyte browser screenshots
- defaults to Zyte's default screenshot format behavior via `jpeg`

Extraction tools:
- support Zyte automatic extraction for `product`, `productList`, `article`, and `pageContent`
- support advanced options like `extract_from`, `session_id`, cookies, and custom attributes

Scrapy Cloud tools:
- use a separate `SCRAPY_CLOUD_API_KEY`
- cover operational job control via `app.zyte.com`
- cover metadata, items, logs, requests, and activity via `storage.zyte.com`
- cover finished-job queue polling via `jobq.zyte.com`
- cover comments reads via `app.zyte.com`
- require explicit `project_id` on every call
- keep outputs normalized to JSON-oriented MCP responses even when upstream endpoints support other formats
- support `spider_args` as an MCP object and flatten them into Scrapy Cloud form fields for `scrapy_cloud_run_spider`

## Advanced Caveats

- `ip_type="residential"` may cost more and requires Zyte KYC
- explicit geolocation choices may affect cost and success rate
- `session_id` is client-managed only in this version
- `custom_attributes` require a standard extraction type and are not supported with `serp`
- browser requests only support `referer` as an initial request header
- Scrapy Cloud uses a different API key from Zyte API
- Scrapy Cloud storage endpoints have irregular pagination semantics; tools currently expose endpoint-native inputs
- Scrapy Cloud mutation support is intentionally limited in this version to running jobs, stopping jobs, and updating job tags
- upstream Scrapy Cloud storage APIs support non-JSON formats, but this server normalizes responses into JSON-friendly MCP outputs

## Test

```bash
uv run pytest
```
