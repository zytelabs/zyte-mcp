"""
Union-merge field dicts from multiple pages.

For each field, we collect every observed value across all pages.
The merger produces:
  - A set of all field names seen on any page.
  - For each field, the list of all observed values (for type inference).
  - Which fields were missing from at least one page (→ Optional).

Output: MergedSchema — the data structure consumed by type_infer and codegen.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MergedSchema:
    """Merged view of fields across all pages."""

    # field_name → list of all non-None values observed across pages
    field_values: dict[str, list[object]] = field(default_factory=dict)

    # Fields that were absent on at least one page (should be Optional)
    optional_fields: set[str] = field(default_factory=set)

    # Ordered list of fields (insertion order = first-seen order)
    field_order: list[str] = field(default_factory=list)

    @property
    def all_fields(self) -> list[str]:
        return self.field_order


def merge(page_fields: list[dict[str, object]]) -> MergedSchema:
    """
    Merge a list of per-page field dicts into a single MergedSchema.

    Args:
        page_fields: One dict per page, each mapping field_name → value.

    Returns:
        MergedSchema with union of all fields, their observed values,
        and which are optional.
    """
    if not page_fields:
        return MergedSchema()

    schema = MergedSchema()

    # Collect all field names in first-seen order
    all_field_names: list[str] = []
    seen: set[str] = set()
    for page in page_fields:
        for name in page:
            if name not in seen:
                all_field_names.append(name)
                seen.add(name)

    schema.field_order = all_field_names

    for name in all_field_names:
        values: list[object] = []
        missing_count = 0

        for page in page_fields:
            value = page.get(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_count += 1
            else:
                values.append(value)

        schema.field_values[name] = values

        if missing_count > 0:
            schema.optional_fields.add(name)

    return schema
