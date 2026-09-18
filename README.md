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
  BL_COMPARISON=129  GENERAL=151  INVOICE_QUERY=75  SI_REQUEST=125  SPAM=40
  comparisons: MISMATCH=46  NEEDS_REVIEW=20  OK=63
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
- All 129 comparison emails reach a definite outcome: 63 `OK`, 46 `MISMATCH`, 20
  `NEEDS_REVIEW`. The corpus contains exactly 20 designed escalation cases (five of each
  cause, `email_501`–`email_520`) and each lands on the reason its own body describes.
- Cross-format pairs work: `email_055` is an `.xlsx` SI against a `.docx` BL and compares
  clean.
- `"No mismatch detected"` is emitted verbatim when all seven fields agree.

**Not real, and deliberately not built:**

- **No OCR and no vision model.** Five PDFs in the corpus are scanned images or corrupt
  files (`email_511`–`email_515`). They are reported `NEEDS_REVIEW / unreadable`, which
  is the honest answer, not a value invented from a picture.
- **Accuracy is unmeasured.** The dataset ships no ground truth, and the bundle does
  **not** include the `score_cli.py` its README mentions. Nothing here has been scored;
  the numbers above are counts of what the pipeline decided, not of what it got right.
- **One classification call is a judgement, not a fact.** 91 emails read "Please assist
  to send the draft BL for … for checking asap" — a request to *be sent* a BL, with
  nothing attached and nothing to compare. They are classified `GENERAL`. If the
  organisers' ground truth calls them `BL_COMPARISON / missing_attachment`, that is 91
  emails wrong in one move. The corpus argues against it: the designed
  `missing_attachment` cases (`email_506`, `508`, `510`) are written separately and
  explicitly, which they would not need to be if this template already covered them.
- **The HTTP/docker path is untested here.** It is supported only because the bundle's
  loader supports it.
- **No submission-form assets.** `docs/RULES.md` records that the form fields, deadline
  and IP terms were never stated; no pitch deck or video was built on a guess.
- The `LICENSE` in this repo is MIT but its copyright holder line is still a placeholder.
  It was left untouched deliberately.

## Layout

```
dock/       the pipeline (stdlib only)
tests/      129 tests; no network, no LLM, deterministic
docs/       the brief, the distilled rules, and the organisers' bundle verbatim
```
