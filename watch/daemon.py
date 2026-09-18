#!/usr/bin/env python3
"""Watch watch/live_inbox/ for new email records and triage them as they land.

Reuses dock.pipeline.process() -- the same function dock/cli.py calls for the
batch run -- so a live-classified email is decided by the identical logic
that produced submission.json, not a second copy of it. See watch/README.md
for what this is and is not.
"""

from __future__ import annotations

import json
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))  # so `import dock` works run from anywhere

from dock.pipeline import explain_entry, process  # noqa: E402
from dock.sources import bundle_inbox  # noqa: E402

LIVE_INBOX = HERE / "live_inbox"
STATE = HERE / "state"
EVENTS = STATE / "events.jsonl"
BOARD = STATE / "board.txt"
LOG = STATE / "daemon.log"
PID_FILE = STATE / "daemon.pid"
POLL_SECONDS = 1.0


def log(msg: str) -> None:
    # print() only: watch-ctl's `nohup ... >>"$LOG" 2>&1` already redirects
    # this process's stdout to the log file. Writing to LOG a second time
    # here duplicated every single line -- caught by an actual feed run, not
    # by inspection; the log read twice as long as the event count implied.
    line = f"{datetime.now(UTC).isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)


def seen_ids() -> set[str]:
    if not EVENTS.is_file():
        return set()
    out = set()
    for line in EVENTS.read_text().splitlines():
        try:
            out.add(json.loads(line)["email_id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def render_board() -> None:
    rows = []
    for line in EVENTS.read_text().splitlines() if EVENTS.is_file() else []:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    lines = [
        f"# live triage -- {len(rows)} email(s) seen",
        f"_watch/daemon.py {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "| email_id | at | outcome |",
        "|---|---|---|",
    ]
    # Every row, newest first. The 200-row cap this replaces silently hid 320
    # of 520 emails after a bulk feed -- the board said "520 email(s) seen"
    # directly above a table that listed 200, which is worse than showing
    # nothing. nvim scrolls a few thousand lines without complaint; if this
    # ever outgrows that, the fix is a filter, not a truncation that does not
    # announce itself.
    for r in reversed(rows):
        lines.append(f"| {r['email_id']} | {r['at'][11:19]} | {r['outcome']} |")
    BOARD.write_text("\n".join(lines) + "\n")


def process_new(inbox, done: set[str]) -> int:
    """One pass: classify any email in live_inbox/ not already in `done`."""
    n = 0
    for f in sorted(LIVE_INBOX.glob("inbox/email_*.json")):
        email_id = f.stem
        if email_id in done:
            continue
        try:
            email = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue  # feeder may still be writing it; catch it next pass
        try:
            entry = process(inbox, email)
        except Exception as exc:
            entry = {
                "category": "ERROR",
                "status": "NEEDS_REVIEW",
                "review_reason": f"daemon exception: {exc}",
                "defect_fields": [],
                "has_defect": False,
            }
        event = {
            "email_id": email_id,
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "entry": entry,
            "outcome": explain_entry(entry)
            if entry.get("category") != "ERROR"
            else entry["review_reason"],
        }
        with EVENTS.open("a") as out:
            out.write(json.dumps(event) + "\n")
        log(f"{email_id}  {event['outcome']}")
        done.add(email_id)
        n += 1
    if n:
        render_board()
    return n


def main() -> int:
    STATE.mkdir(exist_ok=True)
    for d in ("inbox", "attachments"):
        (LIVE_INBOX / d).mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(__import__("os").getpid()))
    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    log(f"watching {LIVE_INBOX} (poll {POLL_SECONDS}s)")
    inbox = bundle_inbox(LIVE_INBOX)
    done = seen_ids()
    render_board()
    while running:
        try:
            process_new(inbox, done)
        except Exception as exc:
            log(f"poll error: {exc}")
        time.sleep(POLL_SECONDS)
    log("stopped")
    PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
