# watch/ — a live triage demo, not the graded deliverable

`dock/` (the package `docs/BRIEF.md` scopes and `dock/cli.py` runs) stays a
batch CLI: read the static dataset, write `submission.json`, exit. That is
what `score_cli.py` grades and what `docs/BRIEF.md` describes — this
directory does not change that, and is not imported by `dock/` or its tests.

What lives here instead is a **watcher**: `daemon.py` polls
`watch/live_inbox/` for new email files and, on arrival, classifies and
compares them through `dock.pipeline.decide()` — the same decision
`dock/cli.py`'s `process()` wraps for the batch run, reused as a library,
not reimplemented — and appends the result to a live event log
(`state/events.jsonl`).

Every `MISMATCH` or `NEEDS_REVIEW` additionally lands in
`state/needs_review.jsonl` — the actual escalation inbox: a strict subset of
the event log containing only the emails a person needs to act on, meant to
be tailed or scripted against, not just read off the dashboard. `./watch-ctl
inbox` renders it.

There is no real live inbox for this hackathon; the dataset is a static
520-email bundle. `feeder.py` is a **demo simulation**: it copies emails from
the real participant bundle into `watch/live_inbox/` on a timer, so the
watcher has something to react to. It never touches `docs/reference/` or
`submission.json`, and it is clearly a separate script so nothing here
pretends the organizers provided a live feed.

The one place this repo calls an LLM at all is `ai_fix.py` (see the `a`
key below) — the daemon, the classify/compare/escalate decision, and the
batch pipeline in `dock/` never do.

## Running it

`watch-ctl` is a Go CLI (`ctl/main.go`) that owns process lifecycle and the
state files only -- start/stop/status/board/inbox/log/feed/resend/delete/
reset. Classification stays in Python: it launches `daemon.py`, which
imports `dock` directly, so there is exactly one implementation of the
pipeline logic, not two.

```bash
cd ctl && go build -o ../watch-ctl . && cd ..   # once; the binary is gitignored

./watch-ctl start                # daemon in the background, PID in state/daemon.pid
./watch-ctl feed 20              # drip 20 sample emails in, ~1 every 2s
./watch-ctl board                # dashboard: charts, flagged detail, full history
./watch-ctl inbox                # the escalation inbox only -- what needs a human
./watch-ctl resend email_004     # edit-and-resend as a new synthetic correction
./watch-ctl aifix email_517      # claude cross-checks blank fields against the other document
./watch-ctl delete email_004-fix110055   # remove a synthetic correction (only "-fix" ids)
./watch-ctl log                  # tail the daemon log (Ctrl-C to stop watching)
./watch-ctl stop
```

`start` is a no-op on an already-running daemon, so editing `daemon.py` and
running `start` leaves you on the old code. `start` and `status` now warn
when the running process predates the last edit; `restart` is what actually
picks a change up.

## The panel

`panel/keys.tsv` + `panel/syntax.tsv` are a panvim view, same mechanism
`hackager`'s own panel and `pr-watch-ctl` use — a terminal dashboard, not a
web server. `./watch-popup` opens it. It is project-local: nothing here
touches `~/.config/panvim` or `~/.local/bin` unless you choose to register a
popup key for it yourself.

With the cursor on any line naming an `email_NNN` id — a flagged card's
`>> email_NNN` header, or a plain row in the full-history table below —
`--row` captures that id for two row-scoped keys:

- **`e`** opens `resend.py` in panvim's sidePan (a real vsplit terminal,
  engine feature). It copies the email's attachments, opens the `.txt`
  ones in `$EDITOR` so a human can fix the value that's wrong, then drops
  the correction into `live_inbox/` as a **brand-new synthetic email**
  (`email_NNN-fixHHMMSS`) for the running daemon to triage on its next
  poll. It never edits the original email, `docs/reference/` or
  `submission.json` — this simulates "someone read the escalation and
  sent a corrected version," nothing more. `.docx`/`.xlsx`/`.pdf`
  attachments are copied as-is; editing those as text would corrupt them,
  so only `.txt` attachments open in the editor.
- **`a`** (`ai_fix.py`) is the AI path: a single, non-interactive
  `claude -p` call reads both the SI and the BL and checks whether each
  blank field is stated on the *other* document. It only ever copies a
  value that's already written down somewhere in what was actually sent —
  never infers or invents one. Scoped to `missing_value` escalations only;
  `wrong_doc_type`/`missing_attachment`/`unreadable` have no text to
  correct from and it refuses those outright, with no API call made. A
  partial fix is normal and correct: if only one of two blank fields is
  recoverable, the resend still comes back `NEEDS_REVIEW` for the other —
  it does not force a false resolution. Same synthetic-email mechanism as
  `e`/`resend.py`; `d`/`delete_email.py` cleans these up too.
- **`d`** (`delete_email.py`) removes that email's files and its lines
  from `events.jsonl`/`needs_review.jsonl`, then re-renders the board
  immediately — but only when the id contains `-fix`. Pressing it on one
  of the 520 real dataset emails is refused outright, so the key can't
  misrepresent what was actually triaged.
