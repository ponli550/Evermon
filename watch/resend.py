#!/usr/bin/env python3
"""Edit-and-resend: take one already-seen email, let a human correct its
attachment(s) in $EDITOR, and drop the correction into live_inbox/ as a
BRAND NEW synthetic email. daemon.py then triages it exactly like any other
arrival, so a corrected SI/BL pair can be shown clearing an escalation live.

What this does NOT do, on purpose: touch docs/reference/ (the real bundle),
touch submission.json, or edit the original email in place. The original
event stays in state/events.jsonl exactly as first decided; this creates a
second, independent email with its own id, its own copied attachments, and
its own triage outcome. There is no live inbox for this hackathon (see
watch/README.md) -- this is a "what if it arrived corrected" demo, not a
correction mechanism for real mail.

Only .txt attachments are opened in $EDITOR -- .docx/.xlsx/.pdf are copied
byte-for-byte (so the pipeline's parser still runs on them) but editing them
as text in an editor would just corrupt them.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_INBOX = HERE / "live_inbox"
BUNDLE = HERE.parent / "docs" / "reference" / "sdoc-hackathon-bundle"


def _find_source(email_id: str) -> tuple[dict, Path]:
    """Return (email record, attachment root) for email_id -- prefer a live
    copy (so re-editing an already-corrected email works too) over the
    original bundle."""
    live = LIVE_INBOX / "inbox" / f"{email_id}.json"
    if live.is_file():
        return json.loads(live.read_text()), LIVE_INBOX
    bundled = BUNDLE / "inbox" / f"{email_id}.json"
    if bundled.is_file():
        return json.loads(bundled.read_text()), BUNDLE
    raise SystemExit(f"no such email: {email_id} (checked live_inbox/ and the bundle)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("email_id", help="the flagged email to correct, e.g. email_004")
    args = ap.parse_args()

    record, att_root = _find_source(args.email_id)
    new_id = f"{args.email_id}-fix{time.strftime('%H%M%S')}"

    editable: list[Path] = []
    new_attachments: list[str] = []
    for att in record.get("attachments") or []:
        src = att_root / att
        dst_rel = f"attachments/{new_id}_{Path(att).name}"
        dst = LIVE_INBOX / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        new_attachments.append(dst_rel)
        if dst.suffix == ".txt":
            editable.append(dst)

    if editable:
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, *[str(p) for p in editable]])
    else:
        print(
            f"{args.email_id} has no .txt attachment to edit here -- copied "
            "as-is (see resend.py's docstring on binary attachments).",
            file=sys.stderr,
        )
        input("press Enter to send it unedited, or Ctrl-C to cancel... ")

    new_record = {
        "email_id": new_id,
        "from": record.get("from", ""),
        "subject": f"[CORRECTED] {record.get('subject', '')}",
        "body": record.get("body", ""),
        "attachments": new_attachments,
    }
    inbox_dir = LIVE_INBOX / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    # Written last, after every attachment is already on disk -- same
    # ordering feeder.py uses, so the daemon never sees a record whose
    # attachments aren't there yet.
    (inbox_dir / f"{new_id}.json").write_text(json.dumps(new_record, indent=2))
    print(f"resent as {new_id} -- the daemon will pick it up within {1.0}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
