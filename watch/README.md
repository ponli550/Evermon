# watch/ — a live triage demo, not the graded deliverable

`dock/` (the package `docs/BRIEF.md` scopes and `dock/cli.py` runs) stays a
batch CLI: read the static dataset, write `submission.json`, exit. That is
what `score_cli.py` grades and what `docs/BRIEF.md` describes — this
directory does not change that, and is not imported by `dock/` or its tests.

What lives here instead is a **watcher**: `daemon.py` polls
`watch/live_inbox/` for new email files and, on arrival, classifies and
compares them through `dock.pipeline.process()` — the exact function
`dock/cli.py` calls for the batch run, reused as a library, not
reimplemented — and appends the result to a live event log.

There is no real live inbox for this hackathon; the dataset is a static
520-email bundle. `feeder.py` is a **demo simulation**: it copies emails from
the real participant bundle into `watch/live_inbox/` on a timer, so the
watcher has something to react to. It never touches `docs/reference/` or
`submission.json`, and it is clearly a separate script so nothing here
pretends the organizers provided a live feed.

## Running it

`watch-ctl` is a Go CLI (`ctl/main.go`) that owns process lifecycle and the
state files only -- start/stop/status/board/log/feed/reset. Classification
stays in Python: it launches `daemon.py`, which imports `dock` directly, so
there is exactly one implementation of the pipeline logic, not two.

```bash
cd ctl && go build -o ../watch-ctl . && cd ..   # once; the binary is gitignored

./watch-ctl start          # daemon in the background, PID in state/daemon.pid
./watch-ctl feed 20        # drip 20 sample emails in, ~1 every 2s
./watch-ctl board          # current triage board, one line per email seen
./watch-ctl log             # tail the daemon log (Ctrl-C to stop watching)
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
