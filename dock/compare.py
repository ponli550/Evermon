"""Stage 3: diff an SI against a draft BL across the seven fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dock.extract import Document
from dock.fields import FIELDS, normalise_value, values_match

#: The exact wording required when every field agrees.
NO_MISMATCH: Final[str] = "No mismatch detected"


@dataclass(frozen=True)
class Comparison:
    status: str
    has_defect: bool
    defect_fields: list[str]
    summary: str
    #: field -> (SI value as compared, BL value as compared); the reviewer's evidence.
    compared: dict[str, tuple[str, str]]


def compare(si: Document, bl: Document) -> Comparison:
    """Compare two documents that are both known to be present, complete and the right type."""
    defects: list[str] = []
    compared: dict[str, tuple[str, str]] = {}
    for name in FIELDS:
        si_value, bl_value = si.values.get(name), bl.values.get(name)
        if si_value is None or bl_value is None:
            continue
        compared[name] = (normalise_value(name, si_value), normalise_value(name, bl_value))
        if not values_match(name, si_value, bl_value):
            defects.append(name)

    if defects:
        listed = ", ".join(defects)
        return Comparison("MISMATCH", True, defects, f"Mismatch on {listed}", compared)
    return Comparison("OK", False, [], NO_MISMATCH, compared)
