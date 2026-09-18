#!/usr/bin/env python3
"""DEMO SIMULATION ONLY. There is no live inbox for this hackathon -- the
dataset is a static 520-email bundle. This drips emails from the real
participant bundle into watch/live_inbox/ on a timer, purely so daemon.py has
something to react to for a demo. It never writes to docs/reference/ or
submission.json, and it is a separate script from everything graded.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "docs" / "reference" / "sdoc-hackathon-bundle"
LIVE_INBOX = HERE / "live_inbox"


def feed_one(email_path: Path) -> str:
    record = json.loads(email_path.read_text())
    for att in record.get("attachments", []):
        src = SOURCE / att
        dst = LIVE_INBOX / att
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    # The email record itself goes in LAST: the daemon only classifies once
    # this file exists, so its attachments are already on disk by then.
    dst = LIVE_INBOX / "inbox" / email_path.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(email_path.read_text())
    return record["email_id"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("count", type=int, nargs="?", default=10, help="how many emails to feed")
    ap.add_argument("--rate", type=float, default=2.0, help="seconds between emails")
    ap.add_argument("--shuffle", action="store_true", help="feed in random order, not email_001..")
    args = ap.parse_args()

    if not SOURCE.is_dir():
        print(f"no participant bundle at {SOURCE}", flush=True)
        return 1
    already = {p.name for p in (LIVE_INBOX / "inbox").glob("email_*.json")} \
        if (LIVE_INBOX / "inbox").is_dir() else set()
    pool = sorted(f for f in SOURCE.glob("inbox/email_*.json") if f.name not in already)
    if args.shuffle:
        import random
        random.shuffle(pool)
    pool = pool[: args.count]
    if not pool:
        print("nothing left to feed (already fed, or count exhausted)", flush=True)
        return 0

    print(f"feeding {len(pool)} email(s) every {args.rate}s from {SOURCE.relative_to(HERE.parent)}",
          flush=True)
    for i, f in enumerate(pool, 1):
        eid = feed_one(f)
        print(f"  [{i}/{len(pool)}] {eid}", flush=True)
        if i < len(pool):
            time.sleep(args.rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
