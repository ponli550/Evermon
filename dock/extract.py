"""Read a rendered document into a document type and the seven comparable values.

Two decisions here matter more than the parsing:

* **Type comes from content, not from the filename.** An attachment called
  ``email_501_BL.txt`` in this corpus is a commercial invoice. Trusting the name would
  compare an invoice against an SI and report confident nonsense.
* **A blank is not a value.** ``N/A``, ``TBA`` and ``____MT`` are a person saying "I did
  not fill this in". They are recorded separately so the pipeline escalates instead of
  reporting a mismatch against a placeholder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from dock.fields import FIELDS, canonical_field, is_blank


class DocumentType(Enum):
    SHIPPING_INSTRUCTION = "SI"
    BILL_OF_LADING = "BL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Document:
    doc_type: DocumentType
    values: dict[str, str] = field(default_factory=dict)
    #: Fields whose label was present but whose value was a placeholder.
    blank_fields: set[str] = field(default_factory=set)

    @property
    def missing_fields(self) -> set[str]:
        """Fields with no usable value, whether absent outright or left blank."""
        return {f for f in FIELDS if f not in self.values}


_LABELLED = re.compile(r"^([^:]{1,70}):\s*(.*)$")
#: Headings are scanned over the opening of the document, not just its first line -
#: a spreadsheet puts the company name above the title.
_HEADING_LINES = 8

# Ordered: "BILL OF LADING INSTRUCTION" is the SI, despite containing "BILL OF LADING".
_TYPE_MARKERS: tuple[tuple[re.Pattern[str], DocumentType], ...] = (
    (
        re.compile(r"(?:BILL OF LADING|B/?L|SHIPPING) INSTRUCTION"),
        DocumentType.SHIPPING_INSTRUCTION,
    ),
    (re.compile(r"PACKING LIST|CERTIFICATE OF ORIGIN|COMMERCIAL INVOICE"), DocumentType.OTHER),
    (re.compile(r"BILL OF LADING|\bB/L\b"), DocumentType.BILL_OF_LADING),
)


def detect_type(text: str) -> DocumentType:
    """Decide what a document is from its own heading."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:_HEADING_LINES]
    head = "\n".join(lines).upper()
    for pattern, doc_type in _TYPE_MARKERS:
        if pattern.search(head):
            return doc_type
    return DocumentType.UNKNOWN


def extract(text: str) -> Document:
    """Parse canonical document text into a Document."""
    values: dict[str, str] = {}
    blanks: set[str] = set()
    for line in text.splitlines():
        if line.startswith((" ", "\t")):
            # A continuation line - part of the address block, not a new field.
            continue
        match = _LABELLED.match(line)
        if match is None:
            continue
        name = canonical_field(match.group(1))
        if name is None or name in values or name in blanks:
            continue
        value = match.group(2).strip()
        if is_blank(value):
            blanks.add(name)
        else:
            values[name] = value
    return Document(doc_type=detect_type(text), values=values, blank_fields=blanks)
