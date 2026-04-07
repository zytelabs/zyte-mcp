"""Shared helpers for building Zyte API payloads and responses."""

from __future__ import annotations

from typing import Any

from zyte_mcp.models import BrowserAction, CookieInput, ExtractionOptions, ZyteRequestOptions


def apply_common_options(payload: dict[str, Any], options: ZyteRequestOptions | ExtractionOptions | None) -> dict[str, Any]:
    if not options:
        return payload

    if options.geolocation:
        payload["geolocation"] = options.geolocation
    if options.ip_type:
        payload["ipType"] = options.ip_type
    if options.request_cookies:
        payload["requestCookies"] = [cookie.model_dump(exclude_none=True) for cookie in options.request_cookies]
    if options.response_cookies:
        payload["responseCookies"] = True
    if options.include_response_headers:
        payload["httpResponseHeaders"] = True
    if options.session_id:
        payload["session"] = {"id": options.session_id}
    if options.tags:
        payload["tags"] = options.tags
    if options.echo_data:
        payload["echoData"] = options.echo_data

    if isinstance(options, ExtractionOptions):
        if options.extract_from:
            payload["extractFrom"] = options.extract_from
        if options.custom_attributes:
            payload["customAttributes"] = options.custom_attributes
        if options.custom_attributes_options:
            payload["customAttributesOptions"] = options.custom_attributes_options

    return payload


def serialize_actions(actions: list[BrowserAction] | None) -> list[dict[str, Any]] | None:
    if not actions:
        return None

    serialized: list[dict[str, Any]] = []
    for action in actions:
        item: dict[str, Any] = {}
        if action.action == "scroll_bottom":
            item["action"] = "scrollBottom"
        elif action.action == "scroll_to":
            item["action"] = "scrollTo"
        elif action.action == "wait_for_selector":
            item["action"] = "waitForSelector"
        elif action.action == "wait_for_timeout":
            item["action"] = "waitForTimeout"
        elif action.action == "key_press":
            item["action"] = "keyPress"
        else:
            item["action"] = action.action

        if action.selector:
            item["selector"] = action.selector.model_dump(exclude_none=True)
        if action.text is not None:
            item["text"] = action.text
        if action.milliseconds is not None:
            item["milliseconds"] = action.milliseconds
        if action.x is not None:
            item["x"] = action.x
        if action.y is not None:
            item["y"] = action.y
        if action.value is not None:
            item["value"] = action.value
        if action.key is not None:
            item["key"] = action.key
        if action.expression is not None:
            item["expression"] = action.expression

        serialized.append(item)

    return serialized


def normalize_response_headers(raw: dict[str, Any]) -> dict[str, Any] | None:
    return raw.get("httpResponseHeaders")


def normalize_response_cookies(raw: dict[str, Any]) -> list[dict[str, Any]] | None:
    cookies = raw.get("responseCookies")
    if isinstance(cookies, list):
        return cookies
    return None
