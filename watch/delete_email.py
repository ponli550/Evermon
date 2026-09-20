#!/usr/bin/env python3
"""Remove one synthetic resend.py email: its live_inbox record, its copied
attachments, and its lines in events.jsonl / needs_review.jsonl -- then
re-render the board immediately, so it's gone from the panel without
waiting for the daemon's next poll.

Restricted to ids containing "-fix" (the suffix resend.py stamps on every
correction it sends). Deleting one of the 520 real dataset emails' history
would misrepresent what was actually triaged during a demo, so that's
refused outright rather than left to whoever's hand is on the key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import daemon  # noqa: E402


def _drop(path: Path, email_id: str) -> None:
    if not path.is_file():
        return
    kept = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            if json.loads(line).get("email_id") == email_id:
                continue
        except json.JSONDecodeError:
            pass
        kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: delete_email.py <email_id>", file=sys.stderr)
        return 2
    email_id = sys.argv[1]
    if "-fix" not in email_id:
        print(
            f"refusing to delete {email_id}: only resend.py's own '-fix' "
            "synthetic emails can be deleted here, not real dataset history.",
            file=sys.stderr,
        )
        return 1

    removed = []
    email_json = daemon.LIVE_INBOX / "inbox" / f"{email_id}.json"
    if email_json.is_file():
        email_json.unlink()
        removed.append(str(email_json))
    for att in daemon.LIVE_INBOX.glob(f"attachments/{email_id}_*"):
        att.unlink()
        removed.append(str(att))

    _drop(daemon.EVENTS, email_id)
    _drop(daemon.NEEDS_REVIEW, email_id)
    daemon.render_board()

    if not removed:
        print(f"{email_id}: no files on disk (already deleted?) -- history entries cleared anyway")
    else:
        for r in removed:
            print(f"removed {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
