"""Render an InferredSchema as an attrs class string."""

from __future__ import annotations

from zyte_mcp.schema.type_infer import FieldSchema, InferredSchema, type_annotation


def _needs_optional(fields: list[FieldSchema]) -> bool:
    return any(f.optional for f in fields)


def _needs_list(fields: list[FieldSchema]) -> bool:
    return any(f.python_type == "list[str]" for f in fields)


def render(schema: InferredSchema) -> str:
    """Return a Python source string for an attrs class."""
    lines: list[str] = []

    # Imports
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import attrs")

    typing_imports: list[str] = []
    if _needs_optional(schema.fields):
        typing_imports.append("Optional")
    if _needs_list(schema.fields):
        typing_imports.append("List")

    if typing_imports:
        lines.append(f"from typing import {', '.join(sorted(typing_imports))}")

    lines.append("")
    lines.append("")
    lines.append("@attrs.define")
    lines.append(f"class {schema.class_name}:")

    if not schema.fields:
        lines.append("    pass")
    else:
        # attrs requires: no-default fields before fields with defaults
        # Group 1: required, non-list (no default)
        # Group 2: required, list[str] (attrs.Factory(list) = has default)
        # Group 3: optional (default=None or Factory)
        required_scalar = [f for f in schema.fields if not f.optional and f.python_type != "list[str]"]
        required_list   = [f for f in schema.fields if not f.optional and f.python_type == "list[str]"]
        optional        = [f for f in schema.fields if f.optional]

        for f in required_scalar:
            annotation = type_annotation(f)
            lines.append(f"    {f.name}: {annotation} = attrs.field()")

        for f in required_list:
            annotation = type_annotation(f)
            lines.append(f"    {f.name}: {annotation} = attrs.Factory(list)")

        for f in optional:
            annotation = type_annotation(f)
            if f.python_type == "list[str]":
                lines.append(f"    {f.name}: {annotation} = attrs.Factory(list)")
            else:
                lines.append(f"    {f.name}: {annotation} = attrs.field(default=None)")

    lines.append("")
    return "\n".join(lines)
