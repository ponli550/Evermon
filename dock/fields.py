"""The seven comparable fields, the vocabulary that names them, and how values compare.

An SI and a draft BL describe the same shipment in different words. "Port of Loading"
on one is "Load Port" on the other; "Gross Wt (kgs)" is "Gross Weight毛重(KGS)". This
module is the single place that resolves a document's header text to a field, and the
single place that decides whether two values mean the same thing.

Alignment is table-driven, not fuzzy: every alias below was harvested from the provided
corpus. Unknown labels return None rather than being guessed at, because a wrong
alignment is a false alarm and false alarms are the expensive failure here.
"""

from __future__ import annotations

import re
from typing import Final

FIELDS: Final[tuple[str, ...]] = (
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
)

#: Field -> every header string seen naming it, across SI and BL vocabularies.
FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "shipper": (
        "Shipper",
        "SHIPPER",
        "Shipper/Exporter",
        "Shipper (Principal or Seller)",
        "Shipper or Exporter",
        "Exporter",
    ),
    "consignee": (
        "Consignee",
        "CONSIGNEE",
        "Consignee (Non-Negotiable)",
        "Consignee Non-Negotiable",
        "To the Order of",
        "To Order of",
    ),
    "notify_party": (
        "Notify",
        "Notify Party",
        "NOTIFY PARTY",
        "Notify Party/Intermediate Consignee",
        "Intermediate Consignee",
    ),
    "port_of_loading": (
        "Port of Loading",
        "PORT OF LOADING",
        "Port of Loading (POL)",
        "POL",
        "Load Port",
        "Loading Port",
        "Port of Receipt",
    ),
    "port_of_discharge": (
        "Port of Discharge",
        "PORT OF DISCHARGE",
        "Port of Discharge (POD)",
        "POD",
        "Discharge Port",
        "Port of Delivery",
    ),
    "container_count": (
        "No. of Containers",
        "No. of Containers or Packages",
        "Number of Containers",
        "Total Containers",
        "Container Count",
        "Containers",
    ),
    "gross_weight_kg": (
        "Gross Weight",
        "GROSS WEIGHT",
        "Gross Weight (KG)",
        "Gross Weight (KGS)",
        "Gross Wt (kgs)",
        "Gross Wt",
        "Gross Weight毛重(KGS)",
    ),
}

#: Labels that look like a field but are not one. Matching these is a false alarm.
DECOY_LABELS: Final[frozenset[str]] = frozenset({"netweight", "netwt", "netweightkgs", "netwtkgs"})

_CJK = re.compile(r"[^\x00-\x7f]+")
#: A parenthetical carrying a CJK gloss - the "(毛重 KGS)" of "Gross Wt (kgs) (毛重 KGS)".
#: It restates the label in another language and adds nothing to align on. Both ASCII and
#: fullwidth brackets count, because a CJK keyboard produces the fullwidth pair.
_BRACKETS = "()" + chr(0xFF08) + chr(0xFF09)
_NOT_BRACKET = f"[^{_BRACKETS}]*"
_CJK_PARENTHETICAL = re.compile(
    f"[({chr(0xFF08)}]{_NOT_BRACKET}[^\\x00-\\x7f]{_NOT_BRACKET}[){chr(0xFF09)}]"
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# A quantity qualifier some documents prefix onto the summary line for a field.
_LABEL_PREFIXES = ("total", "sub")


def normalise_label(label: str) -> str:
    """Reduce a header string to a comparable key: no CJK gloss, no punctuation, no case."""
    stripped = _CJK.sub(" ", _CJK_PARENTHETICAL.sub(" ", label))
    key = _NON_ALNUM.sub("", stripped.lower())
    for prefix in _LABEL_PREFIXES:
        if key.startswith(prefix) and len(key) > len(prefix):
            candidate = key[len(prefix) :]
            if candidate in _ALIAS_INDEX or candidate in DECOY_LABELS:
                return candidate
    return key


_ALIAS_INDEX: Final[dict[str, str]] = {
    _NON_ALNUM.sub("", _CJK.sub(" ", _CJK_PARENTHETICAL.sub(" ", alias)).lower()): field
    for field, aliases in FIELD_ALIASES.items()
    for alias in aliases
}


def canonical_field(label: str) -> str | None:
    """Return the field this header names, or None if it names none of them."""
    key = normalise_label(label)
    if key in DECOY_LABELS:
        return None
    return _ALIAS_INDEX.get(key)


# --- value comparison -------------------------------------------------------

#: A UN/LOCODE tacked onto a port name. Present on one side and absent on the other in
#: this corpus, so it carries no signal and must not be compared.
_LOCODE = re.compile(r"\s*\(\s*[A-Z]{2}[A-Z0-9]{3}\s*\)\s*$")
_WS = re.compile(r"\s+")
_CONTAINERS = re.compile(r"^\s*([\d,]+)\s*(?:x|\*)\s*(.+?)\s*$", re.IGNORECASE)
_NUMBER = re.compile(r"-?[\d,]*\.?\d+")

#: Placeholders a human left in a field they did not fill in.
_BLANK_MARKERS = re.compile(r"^(n/?a|tba|tbc|tbd|nil|none|-+|_+|\.+)$", re.IGNORECASE)


def is_blank(value: str | None) -> bool:
    """True when a value is absent or is a human's placeholder for 'not filled in'."""
    if value is None:
        return True
    text = _WS.sub(" ", value).strip()
    if not text:
        return True
    # "____MT" / "_______ MTS" - underscores plus a unit is still an unfilled blank.
    if re.fullmatch(r"[_\-\.\s]+[A-Za-z]*", text):
        return True
    return bool(_BLANK_MARKERS.match(text))


def _norm_text(value: str) -> str:
    return _WS.sub(" ", value).strip().upper()


def _norm_port(value: str) -> str:
    return _norm_text(_LOCODE.sub("", value.strip()))


def _norm_weight(value: str) -> float | None:
    match = _NUMBER.search(value.replace(" ", ""))
    if match is None:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


def _norm_containers(value: str) -> tuple[str, str] | None:
    match = _CONTAINERS.match(_norm_text(value))
    if match is None:
        return None
    return match.group(1).replace(",", ""), _NON_ALNUM.sub("", match.group(2).lower())


def normalise_value(field: str, value: str) -> str:
    """The comparable form of a value - what is rendered back to a reviewer."""
    if field in ("port_of_loading", "port_of_discharge"):
        return _norm_port(value)
    if field == "gross_weight_kg":
        weight = _norm_weight(value)
        return _norm_text(value) if weight is None else f"{weight:g}"
    if field == "container_count":
        parsed = _norm_containers(value)
        return _norm_text(value) if parsed is None else f"{parsed[0]} x {parsed[1].upper()}"
    return _norm_text(value)


def values_match(field: str, si_value: str, bl_value: str) -> bool:
    """True when the two values mean the same thing for this field."""
    if field == "gross_weight_kg":
        left, right = _norm_weight(si_value), _norm_weight(bl_value)
        if left is not None and right is not None:
            return left == right
    if field == "container_count":
        left_c, right_c = _norm_containers(si_value), _norm_containers(bl_value)
        if left_c is not None and right_c is not None:
            return left_c == right_c
    return normalise_value(field, si_value) == normalise_value(field, bl_value)
