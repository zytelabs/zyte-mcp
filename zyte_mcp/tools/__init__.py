"""Tool registration helpers."""

from zyte_mcp.tools.browser import register_browser_tools
from zyte_mcp.tools.extraction import register_extraction_tools
from zyte_mcp.tools.http import register_http_tools
from zyte_mcp.tools.scrapy_cloud_jobs import register_scrapy_cloud_jobs_tools
from zyte_mcp.tools.scrapy_cloud_storage import register_scrapy_cloud_storage_tools

__all__ = [
    "register_browser_tools",
    "register_extraction_tools",
    "register_http_tools",
    "register_scrapy_cloud_jobs_tools",
    "register_scrapy_cloud_storage_tools",
]
