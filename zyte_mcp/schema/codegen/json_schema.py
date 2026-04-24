"""Render an InferredSchema as a JSON Schema (Draft 2020-12) string."""

from __future__ import annotations

import json

from zyte_mcp.schema.type_infer import FieldSchema, InferredSchema


_PY_TO_JSON: dict[str, object] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list[str]": {"type": "array", "items": {"type": "string"}},
}


def _json_type(field: FieldSchema) -> object:
    base = _PY_TO_JSON.get(field.python_type, "string")
    if field.optional:
        if isinstance(base, dict):
            return {"oneOf": [base, {"type": "null"}]}
        return {"type": [base, "null"]}
    if isinstance(base, dict):
        return base
    return {"type": base}


def render(schema: InferredSchema) -> str:
    """Return a JSON Schema string (pretty-printed)."""
    required_fields = [f.name for f in schema.fields if not f.optional]

    properties: dict[str, object] = {}
    for f in schema.fields:
        prop: dict[str, object] = {}
        json_type = _json_type(f)

        if isinstance(json_type, dict) and "type" in json_type and not isinstance(json_type["type"], list):
            prop.update(json_type)
        else:
            prop.update(json_type if isinstance(json_type, dict) else {"type": json_type})

        if f.example is not None:
            prop["examples"] = [f.example]

        properties[f.name] = prop

    doc: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": schema.class_name,
        "type": "object",
        "properties": properties,
    }

    if required_fields:
        doc["required"] = required_fields

    return json.dumps(doc, indent=2, ensure_ascii=False)
