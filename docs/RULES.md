## Dates

Not stated. The landing page metadata mentions "four days to solve it" but gives no actual start/end dates, timezone, or submission deadline. The Drive folder and README bundle contain no dates either.

## Eligibility

"Open to all enrolled Malaysian university students." Squads of 2 to 5 members (from marketing description: "collaborate in squads of 2 to 5"). No further detail (enrollment proof, one team per person, cross-university teams) is stated.

## Tracks / what to build

Marketing page: "One industry problem, four days to solve it" — single-track industry innovation challenge, no menu of tracks stated.

The actual technical brief comes from the README bundle (SDOC Hackathon), which appears to be the concrete problem statement:

Build a pipeline that reads an email inbox and, for each email, decides:
1. **category** — one of `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`.
2. For `BL_COMPARISON` emails, compare the Shipping Instruction (SI) against the draft Bill of Lading (BL) attachments and report:
   - `status`: `OK` (all 7 fields match), `MISMATCH` (≥1 field differs), or `NEEDS_REVIEW` (undecidable — unreadable/missing/wrong document).
   - `has_defect` + `defect_fields` when `MISMATCH`.
   - `review_reason` when `NEEDS_REVIEW` (`wrong_doc_type` | `missing_attachment` | `unreadable` | `missing_value`).

The 7 compared fields: "shipper, consignee, notify_party, port_of_loading, port_of_discharge, container_count, gross_weight_kg." Note: "the SI and BL often *label the same field differently* (`Port of Loading` vs `Load Port`) — align by meaning, not by header text."

**Where pages disagree**: the landing page never names "SDOC" or shipping documents at all — it's pure marketing copy. The README/problem-statement bundle is the only source with an actual buildable spec. Treat the README as governing for what to build; the landing page only governs dates/prizes/eligibility framing (and even those are thin).

## Hard requirements on the repo and code

- Output must be a `submission.json` that "Match `sample_submission.json` exactly (every email_id present)." (`sample_submission.json` not included in the text supplied — must be in the zip bundles, not fetched here.)
- Quick-start loader code implies stdlib-only path is expected to work: "or use the loader (stdlib only for the .txt path)."
- Scoring is either run for you via `score_cli.py submission.json`, or submitted to an HTTP server: `inbox.submit(submission)["final_score"]`. Neither script's contents, nor server URL, nor auth are stated here.
- No stated requirements on language, license, README format, commit history, or repo structure beyond producing a correct `submission.json`.

## Submission form (every field they ask for)

Not stated. Nothing in the supplied pages describes an actual submission form, portal, or fields (team name, members, pitch deck, video link, etc.). Only the technical output (`submission.json`) is specified in the README — that is not the same thing as an official "submission form."

## Judging criteria (and any stated obvious-vs-creative guidance)

Only a scoring formula is given, and it's for the technical artifact, not necessarily the whole hackathon judging (there's also "pitch live to senior engineering executives" per marketing copy, with no rubric stated for that pitch):

> "Final score = 50% end-to-end (defects caught all the way through) + 30% Stage-1 macro-F1 + 20% Stage-3 defect-F1. `NEEDS_REVIEW` handling is reported as a separate reliability axis."

No obvious-vs-creative guidance stated anywhere.

## Prizes

"Compete for RM 9,000 in cash prizes." No breakdown by place, no stated prize for pitch performance vs. technical score.

## Intellectual property

Not stated. No IP clause appears anywhere in the landing page metadata, the Drive folder listing, or the README bundle.

## What this means for this entry

- The only concrete, buildable spec you have is the SDOC email-classification + SI/BL comparison pipeline from the README — build to that, not to the vague marketing framing.
- You have no dates: don't assume a deadline; confirm start/end/timezone before planning work hours or all-nighters.
- You have no submission-form spec: a tool can produce `submission.json`, but the actual hackathon submission (team registration, pitch deck, demo video, any portal upload) is unspecified and must come from the organizers directly — no amount of code fills that gap.
- The pitch ("pitch live to senior engineering executives") is unscored by any stated rubric and is not something any tool can produce — that's a live human presentation.
- Correctness bar is explicit and machine-checkable: match `sample_submission.json`'s keys/shape exactly, cover every `email_id`, and optimize the stated weighted F1 formula — that part is fully automatable and testable before the deadline (once you have a deadline).
- `NEEDS_REVIEW` is scored separately as a "reliability axis" — don't dump everything into `MISMATCH`/`OK` to game the F1; it's checked independently.
- You don't have `sample_submission.json`, `score_cli.py`, or the server URL in front of you — those exist in the zip bundles (`sdoc-hackathon-bundle.zip`, `sdoc-hackathon-docker.zip`) that were only listed by filename, not fetched/opened. Extract and read them before writing code against assumptions.
- Team size (2–5) and "enrolled Malaysian university student" eligibility are asserted only in SEO meta description text, not an official rules page — verify against whatever real rules doc exists before treating it as binding.
- No IP clause was found anywhere — before submitting original work, get this in writing, since "not stated" here means undocumented, not "no claim."