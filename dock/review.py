"""When to stop and ask a person, and what to tell them.

The scoring treats escalation as its own reliability axis, so the useful behaviour is
narrow: escalate exactly when the pipeline cannot reach a defensible verdict, and say
which of four things went wrong. Anything broader - escalating because a value looked
odd, or because a match was close - turns NEEDS_REVIEW into a shrug and makes the
reliability signal worthless.

The four causes are ordered by how much they hide. An unreadable file could contain
anything, so it outranks a blank field we can at least see.
"""

from __future__ import annotations

from typing import Final

REVIEW_REASONS: Final[tuple[str, ...]] = (
    "wrong_doc_type",
    "missing_attachment",
    "unreadable",
    "missing_value",
)

#: Most obstructive first. The reason reported is the first one that applies.
_PRECEDENCE: Final[tuple[str, ...]] = (
    "missing_attachment",
    "wrong_doc_type",
    "unreadable",
    "missing_value",
)

_EXPLANATIONS: Final[dict[str, str]] = {
    "missing_attachment": "the documents needed for this comparison did not arrive",
    "wrong_doc_type": "an attachment is not the document it was expected to be",
    "unreadable": "an attachment could not be read (scanned image or damaged file)",
    "missing_value": "a compared field was left blank in the source document",
}


def most_obstructive(reasons: set[str]) -> str | None:
    """Pick the reason a reviewer most needs to hear first."""
    for reason in _PRECEDENCE:
        if reason in reasons:
            return reason
    return None


def explain(reason: str, detail: str = "") -> str:
    """A sentence a documentation clerk can act on."""
    base = _EXPLANATIONS[reason]
    return f"{base}: {detail}" if detail else base
