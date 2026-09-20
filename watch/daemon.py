#!/usr/bin/env python3
"""Watch watch/live_inbox/ for new email records and triage them as they land.

Reuses dock.pipeline.decide() -- the same decision dock/cli.py's process()
wraps for the batch run -- so a live-classified email is decided by the
identical logic that produced submission.json, not a second copy of it.
decide() additionally exposes the per-field SI/BL evidence dock/cli.py
doesn't need, for the board's "why flagged" detail. See watch/README.md for
what this is and is not.
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

from dock.classify import CATEGORIES  # noqa: E402
from dock.pipeline import decide, explain_entry  # noqa: E402
from dock.sources import bundle_inbox  # noqa: E402

LIVE_INBOX = HERE / "live_inbox"
STATE = HERE / "state"
EVENTS = STATE / "events.jsonl"
#: The escalation inbox: one line per email a human actually needs to look
#: at (MISMATCH or NEEDS_REVIEW), a strict subset of EVENTS. This is the
#: file the "ask for help" step writes to -- everything else here is a
#: dashboard *reading* what already happened; this is the one file meant to
#: be consumed by something else (a person tailing it, an on-call script).
NEEDS_REVIEW = STATE / "needs_review.jsonl"
BOARD = STATE / "board.txt"
LOG = STATE / "daemon.log"
PID_FILE = STATE / "daemon.pid"
POLL_SECONDS = 1.0

#: outcomes shown in the dashboard's proportion bar, in a fixed order so it
#: doesn't reshuffle its segments as new outcomes show up.
_OUTCOMES = ("OK", "MISMATCH", "NEEDS_REVIEW")


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


def _bar_chart(counts: dict[str, int], order: tuple[str, ...], width: int = 24) -> list[str]:
    """One horizontal bar per key in `order`, scaled to the largest count."""
    peak = max((counts.get(k, 0) for k in order), default=0) or 1
    label_w = max(len(k) for k in order)
    lines = []
    for k in order:
        n = counts.get(k, 0)
        # max(1, ...) so a real but small count never rounds down to an
        # invisible bar -- "2 out of 400" should still show *something*.
        bar = "█" * max(1, round(width * n / peak)) if n else ""
        lines.append(f"  {k.ljust(label_w)}  {bar} {n}")
    return lines


#: one fill character per outcome, used by the proportion bar and its legend.
_OUTCOME_FILL = {"OK": "█", "MISMATCH": "▓", "NEEDS_REVIEW": "░"}


def _proportion_bar(counts: dict[str, int], width: int = 30) -> list[str]:
    """A single stacked bar, OK|MISMATCH|NEEDS_REVIEW by share of total -- the
    pie-chart equivalent that a monospace buffer can actually render clean."""
    total = sum(counts.get(k, 0) for k in _OUTCOMES)
    if total == 0:
        return ["  (no data yet)"]
    segments = []
    used = 0
    for i, k in enumerate(_OUTCOMES):
        seg = width - used if i == len(_OUTCOMES) - 1 else round(width * counts.get(k, 0) / total)
        segments.append(_OUTCOME_FILL[k] * seg)
        used += seg

    def _slice(k: str) -> str:
        n = counts.get(k, 0)
        return f"{_OUTCOME_FILL[k]} {k} {n} ({n * 100 // total}%)"

    return [f"  [{''.join(segments)}]", "  " + "  ".join(_slice(k) for k in _OUTCOMES)]


def _side_by_side(left: list[str], right: list[str], gap: str = "   │  ") -> list[str]:
    left_w = max((len(line) for line in left), default=0)
    height = max(len(left), len(right))
    left = left + [""] * (height - len(left))
    right = right + [""] * (height - len(right))
    return [f"{lft.ljust(left_w)}{gap}{rgt}".rstrip() for lft, rgt in zip(left, right, strict=True)]


def _flagged_card(row: dict, is_latest: bool = False) -> list[str]:
    """Side-by-side SI|BL detail for one flagged (MISMATCH/NEEDS_REVIEW) email."""
    entry = row["entry"]
    tag = " NEW" if is_latest else ""
    lines = [f">>{tag} {row['email_id']}  {row['outcome']}"]
    note = row.get("note") or ""
    if note:
        lines.append(f"   why: {note}")
    compared = row.get("compared") or {}
    if compared:
        defects = set(entry.get("defect_fields") or [])
        field_w = max(len(f) for f in compared)
        val_w = max((len(v) for pair in compared.values() for v in pair), default=3)
        lines.append(f"   {'field'.ljust(field_w)}  {'SI'.ljust(val_w)}  BL")
        for f, (si_val, bl_val) in compared.items():
            flag = "  <-- MISMATCH" if f in defects else ""
            lines.append(f"   {f.ljust(field_w)}  {si_val.ljust(val_w)}  {bl_val}{flag}")
    return lines


def render_board() -> None:
    rows = []
    for line in EVENTS.read_text().splitlines() if EVENTS.is_file() else []:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    category_counts: dict[str, int] = {}
    outcome_counts: dict[str, int] = {}
    for r in rows:
        cat = r["entry"].get("category", "ERROR")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        # Every non-comparison category defaults to status "OK" (dock/pipeline.py's
        # decide() never compared them) -- counting those here would inflate "OK"
        # with emails that were never a comparison in the first place.
        if cat != "BL_COMPARISON":
            continue
        status = r["entry"].get("status")
        if status in _OUTCOMES:
            outcome_counts[status] = outcome_counts.get(status, 0) + 1

    flagged = [
        r for r in reversed(rows) if r["entry"].get("status") in ("MISMATCH", "NEEDS_REVIEW")
    ]

    left = ["## categories", "", *_bar_chart(category_counts, CATEGORIES)]
    right = ["## comparison outcomes", "", *_proportion_bar(outcome_counts)]

    latest_id = rows[-1]["email_id"] if rows else None
    shown = flagged[:12]

    dashboard: list[str] = [
        "# sdoc live triage -- proactive board",
        f"_watch/daemon.py {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        *_side_by_side(left, right),
        "",
        f"## flagged -- {len(flagged)} needing attention (most recent {len(shown)} shown)",
    ]
    if not flagged:
        dashboard.append("  none yet")
    for r in shown:
        dashboard += _flagged_card(r, is_latest=r["email_id"] == latest_id)
    if len(flagged) > len(shown):
        dashboard.append(f"  ... {len(flagged) - len(shown)} more in the full history below")
    dashboard.append("")
    dashboard.append(f"## full history -- {len(rows)} email(s) seen")
    dashboard.append("")

    header = ("email_id", "at", "outcome")
    # Newest first. "at" is stored in UTC isoformat but shown in local time,
    # so the event column reads the same clock as the `_watch/daemon.py`
    # footer above it -- a board that mixed 08:44 (stored) and 16:44 (local)
    # looked like the triage ran six hours in the past.
    body = [
        [
            r["email_id"],
            datetime.fromisoformat(r["at"]).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            f"NEW  {r['outcome']}" if r["email_id"] == latest_id else r["outcome"],
        ]
        for r in reversed(rows)
    ]
    widths = [len(h) for h in header]
    if body:
        for i in range(len(header)):
            widths[i] = max(widths[i], *(len(r[i]) for r in body))

    def row(cells: list[str], dash: str = "") -> str:
        fill = [
            ("-" * max(w, 3) if dash else c.ljust(w)) for c, w in zip(cells, widths, strict=True)
        ]
        return "| " + " | ".join(fill) + " |"

    lines = [
        row(list(header)),
        row(list(header), dash="-"),
    ]
    # Every row, newest first. The 200-row cap this replaces silently hid 320
    # of 520 emails after a bulk feed -- the board said "520 email(s) seen"
    # directly above a table that listed 200, which is worse than showing
    # nothing. nvim scrolls a few thousand lines without complaint; if this
    # ever outgrows that, the fix is a filter, not a truncation that does not
    # announce itself.
    lines += [row(c) for c in body]
    BOARD.write_text("\n".join(dashboard + lines) + "\n")


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
        note = ""
        compared: dict[str, tuple[str, str]] = {}
        try:
            decision = decide(inbox, email)
            entry = {
                "category": decision.category,
                "status": decision.outcome.status,
                "review_reason": decision.outcome.review_reason,
                "defect_fields": decision.outcome.defect_fields,
                "has_defect": decision.outcome.has_defect,
            }
            note = decision.outcome.note
            compared = decision.outcome.compared
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
            "note": note,
            "compared": compared,
            "outcome": explain_entry(entry)
            if entry.get("category") != "ERROR"
            else entry["review_reason"],
        }
        with EVENTS.open("a") as out:
            out.write(json.dumps(event) + "\n")
        if entry["status"] in ("MISMATCH", "NEEDS_REVIEW"):
            with NEEDS_REVIEW.open("a") as out:
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
