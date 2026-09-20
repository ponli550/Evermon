#!/usr/bin/env python3
"""AI-assisted escalation resolution, scoped to exactly one thing: when a
NEEDS_REVIEW email's reason is missing_value, ask Claude (headless,
one-shot, `claude -p`) to check whether each blank field is already stated
on the counterpart document, and copy it over if so -- the same completion
a human reviewer would make, never an invented value.

Every other reason (wrong_doc_type, missing_attachment, unreadable) has no
text to correct from -- there's no document to invent, no missing
attachment to conjure, no OCR pass here. This script refuses those
outright rather than pretend AI can resolve an escalation it has no basis
to resolve. Per field, if the value isn't stated anywhere in what was
actually sent, that field is left alone -- inventing a plausible-looking
number is exactly the failure mode "escalate instead of guessing" exists
to prevent, and that discipline doesn't stop being true just because an
LLM is asking now instead of the rule-based pipeline.

Never touches docs/reference/, submission.json, or the original event.
Creates a brand-new synthetic email (email_NNN-fixHHMMSS, same convention
resend.py uses) for the running daemon to retriage live -- only if at
least one field was actually resolved.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from dock.documents import Unreadable, render  # noqa: E402
from dock.extract import Document, DocumentType, extract  # noqa: E402
from dock.fields import canonical_field  # noqa: E402

LIVE_INBOX = HERE / "live_inbox"
BUNDLE = ROOT / "docs" / "reference" / "sdoc-hackathon-bundle"
STATE = HERE / "state"
#: Full audit trail of every ai_fix.py call: the prompt sent, the raw
#: response, and the verdict -- so "what did the AI actually do" is never
#: just the summary line term-hold happened to still be showing.
AI_LOG = STATE / "ai_fix.log"


def _log(entry: dict) -> None:
    STATE.mkdir(exist_ok=True)
    with AI_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _say(msg: str) -> None:
    print(msg, flush=True)


_PROMPT = """\
This SI/BL pair was escalated because one or more fields were left blank \
on one side. Below are the full text of both documents, and the list of \
blank fields.

SI:
---
{si_text}
---

BL:
---
{bl_text}
---

Blank fields to check: {fields}

For each blank field, is its value clearly and unambiguously stated on \
the OTHER document (the one where it isn't blank)? Only use what is \
literally written above -- never infer, estimate, or invent a value.

Reply with ONLY a JSON object mapping each field name to either the exact \
value as written on the other document, or the string "CANNOT_FIX" if it \
is not stated anywhere above. No other text, no markdown fences.
"""


def _find_source(email_id: str) -> tuple[dict, Path]:
    live = LIVE_INBOX / "inbox" / f"{email_id}.json"
    if live.is_file():
        return json.loads(live.read_text()), LIVE_INBOX
    bundled = BUNDLE / "inbox" / f"{email_id}.json"
    if bundled.is_file():
        return json.loads(bundled.read_text()), BUNDLE
    raise SystemExit(f"no such email: {email_id}")


def _ask_claude(email_id: str, fields: list[str], si_text: str, bl_text: str) -> dict[str, str]:
    prompt = _PROMPT.format(si_text=si_text, bl_text=bl_text, fields=", ".join(fields))
    _say(f"-> asking claude (sonnet, headless) to check: {', '.join(fields)}")
    _say("   (one API round trip, usually a few seconds -- not stuck)")
    started = time.monotonic()
    result = subprocess.run(
        ["claude", "-p", "--model", "sonnet", "--output-format", "json", "--allowedTools", ""],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        _log(
            {
                "email_id": email_id,
                "fields": fields,
                "prompt": prompt,
                "error": result.stderr.strip(),
                "elapsed_s": round(elapsed, 2),
            }
        )
        raise SystemExit(f"claude -p failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    answers = json.loads(payload["result"].strip())
    _say(f"<- claude responded in {elapsed:.1f}s (cost ${payload.get('total_cost_usd', 0):.4f})")
    _log(
        {
            "email_id": email_id,
            "fields": fields,
            "prompt": prompt,
            "raw_result": payload["result"],
            "answers": answers,
            "elapsed_s": round(elapsed, 2),
            "cost_usd": payload.get("total_cost_usd"),
        }
    )
    return answers


def _blank_fields(doc: Document) -> set[str]:
    return doc.blank_fields | doc.missing_fields


def _patch_blank_line(text: str, field: str, value: str) -> str:
    """Replace the blank value on the labelled line naming `field` -- the
    label text itself is untouched, only what comes after the colon."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        label, _, _rest = line.partition(":")
        if canonical_field(label) == field:
            lines[i] = f"{label}: {value}"
            break
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("email_id")
    args = ap.parse_args()

    _say(f"== ai_fix: {args.email_id} ==")
    record, att_root = _find_source(args.email_id)
    attachments = record.get("attachments") or []

    _say(f"reading {len(attachments)} attachment(s)...")
    docs: dict[DocumentType, tuple[str, Path]] = {}
    for att in attachments:
        try:
            text = render(att_root / att)
        except Unreadable as exc:
            print(f"refusing: {att} is unreadable ({exc}) -- nothing to fix from", file=sys.stderr)
            return 1
        doc = extract(text)
        docs[doc.doc_type] = (text, Path(att))

    si = docs.get(DocumentType.SHIPPING_INSTRUCTION)
    bl = docs.get(DocumentType.BILL_OF_LADING)
    if si is None or bl is None:
        print(
            "refusing: need both an SI and a BL to cross-reference -- nothing to fix",
            file=sys.stderr,
        )
        return 1

    si_text, si_path = si
    bl_text, bl_path = bl
    si_doc = extract(si_text)
    bl_doc = extract(bl_text)

    fields = sorted(_blank_fields(si_doc) | _blank_fields(bl_doc))
    if not fields:
        print("no blank fields found -- nothing to fix", file=sys.stderr)
        return 1
    _say(f"blank field(s) to check: {', '.join(fields)}")

    answers = _ask_claude(args.email_id, fields, si_text, bl_text)

    fixed: dict[str, tuple[str, str]] = {}  # field -> (side, value)
    for field in fields:
        value = answers.get(field)
        if not value or value == "CANNOT_FIX":
            _say(f"   {field}: not stated anywhere -- leaving it blank")
            continue
        side = "si" if field in _blank_fields(si_doc) else "bl"
        fixed[field] = (side, value)
        _say(f"   {field}: found {value!r} on the other document")

    if not fixed:
        print("nothing was fixable -- not resending", file=sys.stderr)
        return 1

    new_id = f"{args.email_id}-fix{time.strftime('%H%M%S')}"
    inbox_dir = LIVE_INBOX / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    patched_si, patched_bl = si_text, bl_text
    for field, (side, value) in fixed.items():
        if side == "si":
            patched_si = _patch_blank_line(patched_si, field, value)
        else:
            patched_bl = _patch_blank_line(patched_bl, field, value)

    new_attachments = []
    for att_path, text in ((si_path, patched_si), (bl_path, patched_bl)):
        dst_rel = f"attachments/{new_id}_{att_path.name}"
        dst = LIVE_INBOX / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text)
        new_attachments.append(dst_rel)

    new_record = {
        "email_id": new_id,
        "from": record.get("from", ""),
        "subject": f"[AI-CORRECTED] {record.get('subject', '')}",
        "body": record.get("body", ""),
        "attachments": new_attachments,
    }
    (inbox_dir / f"{new_id}.json").write_text(json.dumps(new_record, indent=2))
    print(f"resent as {new_id} ({len(fixed)}/{len(fields)} blank field(s) resolved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
