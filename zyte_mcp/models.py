"""Shared types for Zyte MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CookieInput(BaseModel):
    name: str
    value: str
    domain: str | None = None
    path: str | None = None


class ActionSelector(BaseModel):
    type: Literal["css", "xpath"]
    value: str
    state: Literal["visible", "attached", "hidden"] | None = None


class BrowserAction(BaseModel):
    action: Literal[
        "click",
        "type",
        "scroll_bottom",
        "scroll_to",
        "wait_for_selector",
        "wait_for_timeout",
        "select",
        "hover",
        "key_press",
        "evaluate",
    ]
    selector: ActionSelector | None = None
    text: str | None = None
    milliseconds: int | None = Field(default=None, ge=0)
    x: int | None = None
    y: int | None = None
    value: str | None = None
    key: str | None = None
    expression: str | None = None


class ZyteRequestOptions(BaseModel):
    geolocation: str | None = None
    ip_type: Literal["datacenter", "residential"] | None = None
    request_cookies: list[CookieInput] | None = None
    response_cookies: bool = False
    include_response_headers: bool = False
    session_id: str | None = None
    tags: dict[str, str] | None = None
    echo_data: dict[str, Any] | None = None


class ExtractionOptions(ZyteRequestOptions):
    extract_from: Literal["httpResponseBody", "browserHtml", "browserHtmlOnly"] | None = None
    custom_attributes: dict[str, Any] | None = None
    custom_attributes_options: dict[str, Any] | None = None


class SerpOptions(BaseModel):
    extract_from: Literal["httpResponseBody", "browserHtml"] = "browserHtml"
    include_iframes: bool = False
