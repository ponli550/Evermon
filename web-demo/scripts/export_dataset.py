#!/usr/bin/env python3
"""Export the real 520-email bundle into web-demo/public/data/emails.json.

This is a BUILD-TIME step, not something the deployed demo runs. It reuses
dock.pipeline.decide() (the exact decision dock/cli.py's process() wraps)
and dock.documents.render() (the exact byte->canonical-text parser dock
uses for .txt/.xlsx/.docx/.pdf) so every value in the exported JSON is what
the real Python pipeline actually produced -- never fabricated for the demo.

What the browser then does with this JSON (web-demo/src/lib/*.ts) is a
hand-ported copy of dock/fields.py + dock/compare.py + dock/review.py's
compare/escalate logic, so a visitor can edit a field and see the SAME
alias-table alignment and comparison rules re-run client-side, in
TypeScript, on top of these real extracted values -- not a second
classification/parsing engine, just the diff layer running twice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dock.documents import Unreadable, render  # noqa: E402
from dock.extract import DocumentType, extract  # noqa: E402
from dock.pipeline import decide  # noqa: E402
from dock.sources import bundle_inbox  # noqa: E402

BUNDLE = ROOT / "docs" / "reference" / "sdoc-hackathon-bundle"
OUT = Path(__file__).resolve().parent.parent / "public" / "data" / "emails.json"


def render_attachment(inbox, path: str) -> dict:
    try:
        payload = inbox.read_bytes(path)
    except OSError as exc:
        return {"path": path, "error": f"could not be fetched ({exc})"}
    import tempfile

    suffix = Path(path).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        tmp = Path(handle.name)
    try:
        text = render(tmp)
    except Unreadable as exc:
        return {"path": path, "error": str(exc)}
    finally:
        tmp.unlink(missing_ok=True)
    doc = extract(text)
    return {
        "path": path,
        "docType": doc.doc_type.value,
        "text": text,
        "fields": doc.values,
        "blankFields": sorted(doc.blank_fields),
    }


def main() -> int:
    inbox = bundle_inbox(BUNDLE)
    out = []
    for email in inbox.emails():
        decision = decide(inbox, email)
        attachments = [render_attachment(inbox, p) for p in (email.get("attachments") or [])]
        si_type = DocumentType.SHIPPING_INSTRUCTION.value
        bl_type = DocumentType.BILL_OF_LADING.value
        si = next((a for a in attachments if a.get("docType") == si_type), None)
        bl = next((a for a in attachments if a.get("docType") == bl_type), None)
        out.append(
            {
                "id": email["email_id"],
                "from": email.get("from", ""),
                "subject": email.get("subject", ""),
                "body": email.get("body", ""),
                "category": decision.category,
                "status": decision.outcome.status,
                "reviewReason": decision.outcome.review_reason,
                "defectFields": decision.outcome.defect_fields,
                "note": decision.outcome.note,
                "si": si,
                "bl": bl,
                "attachmentCount": len(attachments),
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"{len(out)} emails -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
