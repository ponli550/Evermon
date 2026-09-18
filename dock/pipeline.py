"""The agent loop: read an email, decide what it is, and either act on it or escalate.

For a comparison request the run is classify -> read attachments -> identify each
document -> diff the seven fields. At every step there is an exit to NEEDS_REVIEW with a
stated cause, and those are the only exits; the pipeline never returns a verdict it
cannot support from the documents.

Everything else is classified and left alone. An invoice query has no SI and no BL, so
reporting "OK" on it would be meaningless - the neutral verdict exists only because the
submission format requires the keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dock.classify import classify
from dock.compare import NO_MISMATCH, compare
from dock.documents import Unreadable, render
from dock.extract import Document, DocumentType, extract
from dock.review import explain, most_obstructive
from dock.sources import InboxLike

#: How many documents a comparison needs: one SI and one draft BL.
_REQUIRED_DOCUMENTS = 2


@dataclass(frozen=True)
class Attachment:
    path: str
    document: Document | None
    error: Unreadable | None


@dataclass(frozen=True)
class Outcome:
    status: str
    has_defect: bool = False
    defect_fields: list[str] = field(default_factory=list)
    review_reason: str | None = None
    #: Free text for a human reader; not part of the submission format.
    note: str = ""


def _needs_review(reason: str, detail: str = "") -> Outcome:
    return Outcome(status="NEEDS_REVIEW", review_reason=reason, note=explain(reason, detail))


def adjudicate(attachments: list[Attachment]) -> Outcome:
    """Decide the outcome of one comparison request from the documents that arrived."""
    reasons: set[str] = set()
    details: dict[str, str] = {}

    if len(attachments) < _REQUIRED_DOCUMENTS:
        reasons.add("missing_attachment")
        details["missing_attachment"] = (
            f"{len(attachments)} of {_REQUIRED_DOCUMENTS} documents received"
        )

    unreadable = [a for a in attachments if a.document is None]
    if unreadable:
        reasons.add("unreadable")
        details["unreadable"] = "; ".join(str(a.error) for a in unreadable)

    readable = [a.document for a in attachments if a.document is not None]
    si = next((d for d in readable if d.doc_type is DocumentType.SHIPPING_INSTRUCTION), None)
    bl = next((d for d in readable if d.doc_type is DocumentType.BILL_OF_LADING), None)

    if not unreadable and len(attachments) >= _REQUIRED_DOCUMENTS and (si is None or bl is None):
        seen = ", ".join(sorted({d.doc_type.value for d in readable}))
        reasons.add("wrong_doc_type")
        details["wrong_doc_type"] = f"expected an SI and a draft BL, got: {seen or 'nothing'}"

    if si is not None and bl is not None:
        blanks = sorted(si.blank_fields | bl.blank_fields | (si.missing_fields | bl.missing_fields))
        if blanks:
            reasons.add("missing_value")
            details["missing_value"] = ", ".join(blanks)

    reason = most_obstructive(reasons)
    if reason is not None:
        return _needs_review(reason, details.get(reason, ""))
    if si is None or bl is None:
        # Reached only if a document is absent without any cause being recorded.
        return _needs_review("missing_attachment", "no SI/BL pair to compare")

    result = compare(si, bl)
    return Outcome(
        status=result.status,
        has_defect=result.has_defect,
        defect_fields=result.defect_fields,
        note=result.summary,
    )


def read_attachments(inbox: InboxLike, email: dict[str, Any]) -> list[Attachment]:
    """Pull each attachment through the loader and render it to canonical text."""
    out: list[Attachment] = []
    for path in email.get("attachments") or []:
        try:
            text = _render_via_loader(inbox, path)
        except Unreadable as exc:
            out.append(Attachment(path=path, document=None, error=exc))
        else:
            out.append(Attachment(path=path, document=extract(text), error=None))
    return out


def _render_via_loader(inbox: InboxLike, path: str) -> str:
    """Fetch bytes with the bundle's loader, then render them by file type."""
    import tempfile
    from pathlib import Path

    try:
        payload = inbox.read_bytes(path)
    except OSError as exc:
        raise Unreadable(f"{path}: could not be fetched ({exc})") from exc
    suffix = Path(path).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    try:
        return render(temporary)
    finally:
        temporary.unlink(missing_ok=True)


def process(inbox: InboxLike, email: dict[str, Any]) -> dict[str, Any]:
    """Run one email through the pipeline and return its submission entry."""
    category = classify(email)
    if category != "BL_COMPARISON":
        outcome = Outcome(status="OK", note="not a document comparison request")
    else:
        outcome = adjudicate(read_attachments(inbox, email))
    return {
        "category": category,
        "status": outcome.status,
        "review_reason": outcome.review_reason,
        "defect_fields": outcome.defect_fields,
        "has_defect": outcome.has_defect,
    }


def explain_entry(entry: dict[str, Any]) -> str:
    """One line of human-readable reasoning, for --explain."""
    if entry["category"] != "BL_COMPARISON":
        return f"{entry['category']}"
    if entry["status"] == "NEEDS_REVIEW":
        return f"NEEDS_REVIEW ({entry['review_reason']})"
    if entry["status"] == "MISMATCH":
        return f"MISMATCH on {', '.join(entry['defect_fields'])}"
    return NO_MISMATCH
