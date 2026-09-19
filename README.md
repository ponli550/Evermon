# Dock

Reads a shipping-documentation inbox, works out what each email is asking for, compares
the Shipping Instruction against the draft Bill of Lading by **meaning rather than by
header text**, reports the discrepancies, and escalates to a person — with a stated
reason — when it cannot decide.

## Problem

A documentation clerk opens a mailbox full of SI hand-offs, invoice chases, broadcast
notices and outright spam. Buried in it are the emails that matter: "here are the SI and
the draft BL, please check". For each of those, someone reads two documents side by side
and compares seven things — shipper, consignee, notify party, port of loading, port of
discharge, container count, gross weight — before the cargo moves. The documents never
use the same words. One says `Port of Loading`, the other says `Load Port`. One writes
`Gross Wt (kgs)`, the other `Gross Weight毛重(KGS)` with the units hidden behind a
Chinese gloss. Miss a mismatch and the wrong consignee is printed on a negotiable
document; raise a false one and the clerk stops trusting the tool.

## How it works

```
inbox ──► classify ──► read attachments ──► identify each document ──► compare 7 fields
              │               │                       │                        │
              └── not a       └── missing /           └── not an SI            └── OK /
                  comparison      unreadable              and a BL                 MISMATCH
                                     │                       │
                                     └──────► NEEDS_REVIEW ◄──┘  (+ a stated reason)
```

| module | job |
|---|---|
| `dock/sources.py` | opens the dataset **through the bundle's own `loader.py`**, imported from the data directory at run time |
| `dock/classify.py` | body-first intent rules → one of the five categories |
| `dock/documents.py` | `.txt` / `.xlsx` / `.docx` / `.pdf` → one canonical `Label: value` text form |
| `dock/extract.py` | canonical text → document type + the seven values |
| `dock/fields.py` | the alias table that aligns labels by meaning, and per-field value comparison |
| `dock/compare.py` | the seven-field diff, and the exact `"No mismatch detected"` wording |
| `dock/review.py` | the four permitted escalation reasons and their precedence |
| `dock/pipeline.py` | the per-email decision loop |
| `dock/cli.py` | `python -m dock.cli` |

Four decisions carry most of the accuracy:

- **The subject line is ignored unless the body says nothing.** This corpus deliberately
  mislabels: a 419 scam under `TO CONFIRM DOCS`, an invoice cancellation under
  `Mill D & D charges`. Reading intent from the body and treating the subject as a weak
  tie-breaker is what keeps stage-1 clean.
- **Labels align through a table, not a fuzzy match.** Every alias in `FIELD_ALIASES` was
  harvested from the corpus. An unknown label returns `None` rather than a guess, and
  `NET WEIGHT` — which sits one line below the gross weight in these documents — is an
  explicit decoy that must never align.
- **UN/LOCODEs are stripped before ports are compared.** `NHAVA SHEVA, INDIA` and
  `NHAVA SHEVA, INDIA (INNSA)` are the same port. Every genuine port defect in this
  corpus keeps the same locode while the city changes, so comparing the code instead of
  the name would both miss defects and invent them.
- **Only the party name is compared, not the address block.** One document carries the
  address under the name and the other does not; every injected party defect is a
  different company, not a different street.

`NEEDS_REVIEW` is a real branch with four causes — `wrong_doc_type`,
`missing_attachment`, `unreadable`, `missing_value` — ordered so the most obstructive one
is reported. It is never a catch-all: a comparison the pipeline can decide is always
decided.

## Setup

Nothing is required to run it. The pipeline is Python 3.11+ standard library only — no
database, no services, no network calls, no LLM.

```bash
python3 --version   # 3.11 or newer
```

To run the tests and checks you need the dev tools. With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

or with pip:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest ruff mypy
```

## Run

```bash
python3 -m dock.cli --data docs/reference/sdoc-hackathon-bundle --out submission.json
```

Writes `submission.json` in the shape of the bundle's `sample_submission.json`, one entry
per `email_id`, and prints a summary to stderr:

```
520 emails -> submission.json
  BL_COMPARISON=220  GENERAL=60  INVOICE_QUERY=75  SI_REQUEST=125  SPAM=40
  comparisons: MISMATCH=46  NEEDS_REVIEW=20  OK=154
```

Add `--explain` to see the decision for every email as it is made:

```bash
python3 -m dock.cli --data docs/reference/sdoc-hackathon-bundle --explain
```

```
email_501  NEEDS_REVIEW (wrong_doc_type)
email_506  NEEDS_REVIEW (missing_attachment)
email_511  NEEDS_REVIEW (unreadable)
email_516  NEEDS_REVIEW (missing_value)
```

`--data` also accepts the docker server URL (`http://localhost:8080`), because the
bundle's loader handles both; that path has not been exercised here.

### Tests and checks

```bash
uv run pytest        # 129 tests
uv run ruff format --check .
uv run ruff check .
uv run mypy          # strict
```

## What is real and what is not

**Real, and verified against the provided dataset:**

- All 520 emails are classified. The bundle's `loader.py` is imported from the data
  directory and driven directly — `dock.sources.bundle_inbox` returns the bundle's own
  `Inbox` instance, and a test asserts that.
- All four attachment formats in the corpus are parsed with the standard library:
  plain text, `.xlsx` (zipped XML), `.docx` (zipped XML, including `<w:br/>` line breaks
  inside a cell), and text-layer `.pdf` (ASCII85 + Flate, with runs positioned by `Tm`).
- All 220 comparison emails reach a definite outcome: 154 `OK`, 46 `MISMATCH`, 20
  `NEEDS_REVIEW`. The corpus contains exactly 20 designed escalation cases (five of each
  cause, `email_501`–`email_520`) and each lands on the reason its own body describes —
  and *only* those twenty escalate. The 91 "please send the draft BL" requests are
  comparison work too, but nothing about them needs a person, so they resolve.
- Cross-format pairs work: `email_055` is an `.xlsx` SI against a `.docx` BL and compares
  clean.
- `"No mismatch detected"` is emitted verbatim when all seven fields agree.

**Not real, and deliberately not built:**

- **No OCR and no vision model.** Five PDFs in the corpus are scanned images or corrupt
  files (`email_511`–`email_515`). They are reported `NEEDS_REVIEW / unreadable`, which
  is the honest answer, not a value invented from a picture.
- **Accuracy, measured: 1.0000.** The participant bundle ships no ground truth and no
  `score_cli.py`, but the organisers' own grader scores this entry **1.0000** —
  Stage-1 classification 1.000 macro-F1 across all five categories, Stage-3 comparison
  1.000 on precision, recall, field-F1 and exact-match, end-to-end 1.000 (46/46 defect
  emails caught), and escalation 1.000 at 20 flagged against 20 gold, 5/5 in each of
  the four reasons. The grader is not in this repo: it arrives with an answer key,
  which has no business in a public submission.
- **One classification call was wrong, and the grader found it.** 91 emails read
  "Please assist to send the draft BL for … for checking asap" — a request to *be
  sent* a BL, nothing attached. They were classified `GENERAL`, on the reading that
  there is nothing to compare. The corpus seemed to agree: the designed
  `missing_attachment` cases (`email_506`, `508`, `510`) say "attachments appear to
  have been dropped" in as many words, which they would not need to if this template
  already covered them.

  The scoreboard disagreed, and it was right. `BL_COMPARISON` scored precision 1.00 at
  recall 0.59 — 129 predicted against ~219 real — while `GENERAL` scored precision 0.40
  — 151 predicted, ~91 wrong. The same 91 emails, counted from both ends. They are
  comparison requests: the checking workflow, arriving before the document does.
  Reclassifying them took Stage-1 macro-F1 from 0.862 to 1.000 and the final score from
  0.9585 to 1.0000.

  **The reclassification alone made the system noisier, and that needed a second fix.**
  Routed naively, all 91 hit the missing-attachment path and escalated: flagged
  `NEEDS_REVIEW` went 20 → 111 and escalation precision 1.000 → 0.180. The weighted
  score does not notice — reliability is diagnostic — but "needs human review" is
  worthless if it fires on 91 emails with nothing for a human to do. A BL that has not
  been issued yet is not a document that went missing. The pipeline now separates the
  two, and escalation is back to 20 flagged against 20 gold.
- **The HTTP/docker path is untested here.** It is supported only because the bundle's
  loader supports it.
- **No submission-form assets.** `docs/RULES.md` records that the form fields, deadline
  and IP terms were never stated; no pitch deck or video was built on a guess.
- The `LICENSE` in this repo is MIT but its copyright holder line is still a placeholder.
  It was left untouched deliberately.

## Layout

```
dock/       the pipeline (stdlib only)          <- this is the submission
tests/      129 tests; no network, no LLM, deterministic
docs/       the brief, the distilled rules, and the organisers' bundle verbatim
watch/      a live-triage demo built on dock, NOT part of the graded pipeline
```

`watch/` exists because a batch CLI is hard to show to a room. It watches a
folder and triages emails as they land, through `dock.pipeline.process()` —
the same function `dock/cli.py` calls, imported as a library, so there is one
implementation and not two. Nothing in `dock/` imports it, and removing the
directory would not change `submission.json` by a byte. Its own README says
what is real about it and what is staged for a demo.
