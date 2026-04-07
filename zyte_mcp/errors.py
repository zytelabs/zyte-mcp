"""Error types and translation helpers for Zyte API failures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ZyteAPIError(Exception):
    status_code: int
    error_type: str | None
    detail: str
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.error_type:
            return f"Zyte API error {self.status_code} ({self.error_type}): {self.detail}"
        return f"Zyte API error {self.status_code}: {self.detail}"


@dataclass(slots=True)
class ZyteRequestValidationError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


def build_zyte_error(status_code: int, payload: dict[str, Any] | None) -> ZyteAPIError:
    payload = payload or {}
    error_type = payload.get("type")
    detail = payload.get("detail") or payload.get("title") or "Request failed"
    return ZyteAPIError(
        status_code=status_code,
        error_type=error_type,
        detail=detail,
        payload=payload,
    )


def is_retryable_error(status_code: int, error_type: str | None) -> bool:
    if status_code in {429, 503}:
        return True
    if status_code == 520:
        return True
    if status_code == 521 and error_type == "/download/internal-error":
        return True
    return False
