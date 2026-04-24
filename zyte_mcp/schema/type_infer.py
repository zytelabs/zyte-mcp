"""
Infer Python types from observed field values.

Rules (cascade from most specific to least):
  - list[str]     if any value is a Python list
  - bool          if ALL values are boolean-ish strings (true/false/yes/no/on/off)
  - int           if ALL values parse as integers (and none are floats)
  - float         if ALL values parse as floats (may include ints)
  - str           otherwise

Wraps in Optional[T] if the field was absent on at least one page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from zyte_mcp.schema.merger import MergedSchema


@dataclass
class FieldSchema:
    name: str
    python_type: str       # e.g. "str", "int", "float", "list[str]", "bool"
    optional: bool         # True → rendered as Optional[T]
    example: object | None = None  # first observed value, for documentation


@dataclass
class InferredSchema:
    class_name: str
    fields: list[FieldSchema]


_BOOL_TRUE = {"true", "yes", "1", "on"}
_BOOL_FALSE = {"false", "no", "0", "off"}
_BOOL_VALUES = _BOOL_TRUE | _BOOL_FALSE

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?[\d,]+\.?\d*$")  # allows comma thousands separators

_LEADING_CURRENCY_RE = re.compile(r"^[£$€¥₹\+\-\s]*")
_TRAILING_CURRENCY_RE = re.compile(r"[\s%a-zA-Z]*$")


def _strip_currency(s: str) -> str:
    """Strip leading currency symbols/whitespace and trailing units for numeric parsing."""
    s = _LEADING_CURRENCY_RE.sub("", s)
    s = _TRAILING_CURRENCY_RE.sub("", s)
    return s.replace(",", "")


def _infer_single(values: list[object]) -> str:
    """Infer the Python type string for a list of observed values."""
    if not values:
        return "str"

    # If any value is a list, treat the field as list[str]
    if any(isinstance(v, list) for v in values):
        return "list[str]"

    # Normalise everything to strings for further checks
    str_values = [str(v).strip() for v in values if v is not None]
    if not str_values:
        return "str"

    # Boolean check
    lower_vals = [s.lower() for s in str_values]
    if all(v in _BOOL_VALUES for v in lower_vals):
        return "bool"

    # Numeric check: strip currency/unit wrappers, then test.
    cleaned = [_strip_currency(s) for s in str_values]
    if not all(cleaned):  # at least one became empty after strip — can't be numeric
        return "str"

    # Integer check
    if all(_INT_RE.match(c) for c in cleaned):
        return "int"

    # Float check
    if all(_FLOAT_RE.match(c) for c in cleaned):
        return "float"

    return "str"


def infer(schema: MergedSchema, class_name: str) -> InferredSchema:
    """
    Produce an InferredSchema from a MergedSchema.

    Args:
        schema:     The merged schema from merger.merge().
        class_name: The desired Python class name.

    Returns:
        InferredSchema ready for code generation.
    """
    fields: list[FieldSchema] = []

    for name in schema.field_order:
        values = schema.field_values.get(name, [])
        optional = name in schema.optional_fields
        python_type = _infer_single(values)
        example = values[0] if values else None

        fields.append(
            FieldSchema(
                name=name,
                python_type=python_type,
                optional=optional,
                example=example,
            )
        )

    return InferredSchema(class_name=class_name, fields=fields)


def type_annotation(field: FieldSchema) -> str:
    """Return the full Python type annotation string for a field."""
    t = field.python_type
    if field.optional:
        return f"Optional[{t}]"
    return t
