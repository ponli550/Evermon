# Evermon — Technical Documentation

## Technical Architecture

Evermon is two things sharing one core: a graded batch pipeline (`dock/`) and an
optional live-triage demo built on top of it (`watch/`). Only `dock/` is
scored; `watch/` exists to make a batch CLI demonstrable in a room.

### The pipeline (`dock/`)

```
inbox ──► classify ──► read attachments ──► identify each document ──► compare 7 fields
              │               │                       │                        │
              └── not a       └── missing /           └── not an SI            └── OK /
                  comparison      unreadable              and a BL                 MISMATCH
                                     │                       │
                                     └──────► NEEDS_REVIEW ◄──┘  (+ a stated reason)
```

| module | responsibility |
|---|---|
| `dock/sources.py` | opens the dataset through the bundle's own `loader.py`, imported at runtime from the data directory (falls back to a stdlib-only reader if `loader.py` is absent) |
| `dock/classify.py` | body-first intent rules → one of `BL_COMPARISON` / `SI_REQUEST` / `INVOICE_QUERY` / `GENERAL` / `SPAM` |
| `dock/documents.py` | `.txt` / `.xlsx` / `.docx` / `.pdf` → one canonical `Label: value` text form |
| `dock/extract.py` | canonical text → document type (SI vs. draft BL) + the seven field values |
| `dock/fields.py` | the alias table that aligns labels by meaning, and per-field value comparison (locode stripping, unit normalisation) |
| `dock/compare.py` | the seven-field diff, and the exact `"No mismatch detected"` string |
| `dock/review.py` | the four permitted escalation reasons and their precedence order |
| `dock/pipeline.py` | `decide()` — the per-email decision loop; `process()` — the thin wrapper that shapes `decide()`'s output into the submission schema |
| `dock/cli.py` | `python -m dock.cli --data <bundle> --out submission.json` |

Stack: Python 3.11+, standard library only (`dependencies = []` in
`pyproject.toml`). No database, no network calls, no LLM, no vision model in
the graded path. 1,124 lines across `dock/`, 129 tests in `tests/`.

### The live-triage demo (`watch/`, not graded)

```
live_inbox/ (files) ──poll(1s)──► daemon.py ──► dock.pipeline.decide() ──► state/*.jsonl ──► board.txt
                                                                                   │
                                                                    watch-ctl (Go) reads/renders it
                                                                                   │
                                                                    watch-popup → panvim terminal panel
```

- `daemon.py` polls `watch/live_inbox/` and classifies arrivals through
  `dock.pipeline.decide()` — the exact decision `dock/cli.py`'s `process()`
  wraps, reused as a library. One implementation, not two.
- `watch-ctl` (Go, `ctl/main.go`) owns process lifecycle and the state
  files: `start | stop | restart | status | board | inbox | feed | resend |
  aifix | delete | log | reset`.
- `watch-popup` (Go, `popup/main.go`) opens the dashboard as a `panvim`
  terminal panel — a live-reloading text view, not a web UI.
- `state/events.jsonl` — every decision, ever. `state/needs_review.jsonl` —
  the actual escalation inbox, a strict subset (`MISMATCH`/`NEEDS_REVIEW`
  only), meant to be tailed or scripted against.
- `resend.py` / `delete_email.py` — an edit-and-resend loop: copy a flagged
  email's attachments, edit the `.txt` ones in `$EDITOR`, resubmit as a
  brand-new synthetic email (`email_NNN-fixHHMMSS`) for the daemon to
  retriage live. Delete is restricted to `-fix` ids only — it cannot touch
  real dataset history.
- `ai_fix.py` — the one place this repo calls an LLM. A single headless
  `claude -p` call per escalation, scoped to `missing_value` only: it
  reads the SI and the BL together and copies a blank field's value over
  *only* when the counterpart document already states it — never infers
  or invents one. Same synthetic-email mechanism as `resend.py`.

## Implementation Details

**Classification is body-first.** The corpus deliberately mislabels subject
lines (a 419 scam under `TO CONFIRM DOCS`, an invoice cancellation under
`Mill D & D charges`). `classify.py` reads intent from the body and treats
the subject as a weak tie-breaker only when the body says nothing — this is
what keeps Stage-1 classification clean against a corpus built to punish
subject-line shortcuts.

**Field alignment is a table, not a fuzzy match.** Every alias in
`FIELD_ALIASES` was harvested from the corpus by hand. An unrecognised label
returns `None` rather than a guess, and `NET WEIGHT` — one line below gross
weight in these documents — is an explicit decoy that must never align to
`gross_weight_kg`.

**UN/LOCODEs are stripped before ports are compared.** `NHAVA SHEVA, INDIA`
and `NHAVA SHEVA, INDIA (INNSA)` are the same port; every genuine port
defect in the corpus keeps the same locode while the city name changes, so
comparing the code instead of the city would both miss real defects and
invent false ones.

**Only the party name is compared, not the address block.** One document
carries the address under the party name and the other does not; every
injected shipper/consignee defect changes the company, not the street.

**Document parsing is stdlib-only.** `.xlsx` and `.docx` are zipped XML,
parsed with `zipfile` + `xml.etree`, including `<w:br/>` line breaks inside
a Word table cell. `.pdf` text layers are extracted by walking ASCII85/Flate
content streams and reconstructing lines from `Tm`-positioned text runs —
no PDF library, no OCR, no vision model. Five PDFs in the corpus are scanned
images or corrupt; those correctly resolve to `NEEDS_REVIEW / unreadable`.

**`NEEDS_REVIEW` has four causes, precedence-ordered** in `review.py`:
`missing_attachment` > `wrong_doc_type` > `unreadable` > `missing_value` —
ordered by how much each one hides (an unreadable file could contain
anything; a blank field, at least you can see what's missing). It is never
a catch-all: every comparison the pipeline can decide, it decides.

**AI is scoped to what it can prove, never to what it can guess.**
`watch/ai_fix.py` reads both documents and cross-checks each blank field
against the other side — the same completion a human reviewer would make.
It refuses outright, with zero API calls, on `wrong_doc_type`/
`missing_attachment`/`unreadable` (there's no text to correct from), and
per-field on `missing_value` when the value isn't stated anywhere in what
was actually sent. A partial fix is normal: `email_517` has two blank
fields, one recoverable from the other document and one genuinely blank on
both sides — the AI fixes the first and correctly leaves the email
`NEEDS_REVIEW` for the second, rather than forcing a false resolution.

**`dock.pipeline.decide()` vs `process()`.** `decide()` returns the full
internal `Outcome` — including `compared` (the per-field SI/BL values that
`compare()` computes but the submission schema doesn't need) and a
human-readable `note`. `process()` is a thin wrapper that shapes that into
exactly the four/five keys `submission.json` requires. This split exists so
`watch/`'s live dashboard can show *why* something was flagged, side by
side, without a second implementation of the decision logic.

## Challenges Faced

**A wrong classification call that only the scoring caught.** 91 emails
read "Please assist to send the draft BL for … for checking asap" — a
request to *be sent* a BL, nothing attached yet. These were first
classified `GENERAL` on the reasoning that there's nothing to compare. The
corpus's own designed `missing_attachment` cases (`email_506/508/510`) say
"attachments appear to have been dropped" — different wording from "please
send," which seemed to confirm the two were distinct. The scoreboard
disagreed: `BL_COMPARISON` recall was 0.59 (129 predicted vs. ~219 real)
while `GENERAL` precision was 0.40 (151 predicted, ~91 wrong) — the same 91
emails, counted from both ends. Reclassifying them as `BL_COMPARISON` (with
`status: OK`, since there's genuinely nothing to compare yet) took Stage-1
macro-F1 from 0.862 to 1.000.

**That fix made the system noisier, and needed a second fix.** Routed
naively, all 91 "handover request" emails hit the missing-attachment path
and escalated: flagged `NEEDS_REVIEW` went from 20 to 111, and escalation
precision collapsed from 1.000 to 0.180. The weighted score doesn't
penalise this (reliability is reported as a separate axis), but a
"needs human review" flag that fires on 91 emails with nothing for a human
to actually do is worthless. `pipeline.py` now special-cases the
`bl_handover_request` reason to resolve `OK` directly, and escalation is
back to exactly 20 flagged against 20 designed cases.

**A stray background process caused a silent duplicate.** During
`watch/`'s edit-and-resend testing, a `daemon.py` instance left running from
earlier in the same session picked up a freshly created correction and
triaged it *before* the intended edit was applied — producing two log
entries for the same synthetic email (one stale `MISMATCH`, one correct
`OK`) and briefly looking like a bug in `resend.py`. It wasn't: two
processes were racing over the same `live_inbox/`. The fix was operational
(`watch-ctl stop`), not code — but it's a real caveat of the daemon model:
nothing prevents two instances polling the same directory.

**A third-party tool bug, not ours.** `hackager slides .` (relative path)
silently wrote the pitch deck to a hidden dotfile — `docs/.pptx`, an empty
basename — instead of a real filename. Passing the absolute project path
worked correctly. Filed upstream; worked around here by always resolving
the path first.

**Deliberately not built:** OCR/vision for the five scanned/corrupt PDFs
(`email_511`–`515`) — reporting `NEEDS_REVIEW / unreadable` is the honest
answer, not a value invented from a picture. The Docker/HTTP loader path is
supported (the bundle's `loader.py` handles it) but untested here, since
only the static bundle was available to develop against.

## Future Roadmap

- **OCR or a vision-LLM fallback for scanned PDFs** — currently the five
  scanned/corrupt attachments correctly escalate rather than guess; a
  vision pass could resolve some of them, but only if it can itself be
  audited (no black-box field extraction without a stated confidence and
  fallback to `NEEDS_REVIEW`).
- **An actual push-based escalation**, not just a pollable file. Today
  `state/needs_review.jsonl` is a file a person or script must tail; a
  desktop notification, webhook, or terminal bell on write is a small,
  scoped addition (fires from `daemon.py`'s existing `process_new()` loop)
  that turns "ask for help" from passive into interrupt-driven.
- **A daemon single-instance guard.** The stray-process incident above is
  a real gap: nothing stops two `daemon.py` processes from polling the same
  `live_inbox/` concurrently. A pidfile-based lock (beyond the existing
  informational `state/daemon.pid`) would make that a hard error instead of
  a silent duplicate.
- **Exercise the Docker/HTTP loader path** the bundle ships but this
  project never ran against, so `--data http://localhost:8080` is
  supported in theory (the loader interface is identical) but unverified.
- **Confirm the actual submission requirements** — `docs/RULES.md` records
  that deadlines, submission-form fields, and video requirements were
  unstated when this was built. A pitch deck and PDF now exist
  (`docs/AverisMonash2026.pptx`, `docs/PITCH.pdf`); a demo video was
  deliberately deferred until the requirement is confirmed, rather than
  spending real API cost and runtime building an asset against a guess.
