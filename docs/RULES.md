## Dates

not stated. The marketing page says "four days to solve it" but gives no calendar dates, deadlines, or timezone. Treat this as unresolved until confirmed elsewhere — do not assume a submission cutoff.

## Eligibility

"Open to all enrolled Malaysian university students." Squads of 2 to 5 (from marketing meta description: "collaborate in squads of 2 to 5"). No further eligibility detail (verification method, one-team-per-person rule, etc.) is stated.

## Tracks / what to build

Single problem, not multiple tracks: **shipping document verification**, from email inbox to discrepancy report. The system must, per email:

- **Classify** into one of: `BL_COMPARISON` (or "document-comparison request" in the readthis doc), `SI_REQUEST`/"new SI requests", `INVOICE_QUERY`, `GENERAL`, `SPAM`.
- **Extract** SI and BL attachment fields (only for comparison requests).
- **Compare** 7 fields: shipper, consignee, notify party, port of loading, port of discharge, container count, gross weight (kg). Field labels differ across documents (e.g. "Port of Loading" vs "Load Port") — must align by meaning, not header text.
- **Ask for help**: escalate to human-in-the-loop when it can't decide, "rather than guessing or failing silently."

Baseline: JSON email records, plain-text attachments. **Advanced stage** (explicitly optional, for standing out): PDF/Word attachments with tables/layouts, scanned/image-only PDFs (OCR or vision LLM), messier inputs (varied labels, misleading subjects, missing attachments), and formal `NEEDS_REVIEW` handling with reasons (`wrong_doc_type`, `missing_attachment`, `unreadable`, `missing_value`).

Output shape (only required if using self-eval, but is the de facto contract): one JSON object keyed by `email_id`, matching `sample_submission.json` exactly, every email present. Per README: `category`, and for `BL_COMPARISON`: `status` (`OK`/`MISMATCH`/`NEEDS_REVIEW`), `has_defect`, `defect_fields`, `review_reason`.

## Hard requirements on the repo and code

None stated explicitly as submission-repo rules (no license file requirement, no README requirement, no language restriction stated). What's implied by the tooling:
- Must be runnable against the provided dataset via `loader.py` (`Inbox("data")` or a server URL) — plain stdlib works for the `.txt` path per README.
- Docker option available (`docker compose up --build`, serves at `localhost:8080`) but "not stated" whether Docker is mandatory for judging — README says no DB/setup needed, implying it's optional convenience.
- Self-evaluation via `POST /submit` or `score_cli.py submission.json` is optional/dev-only, "not the final assessment."
- No stated requirement to use LLMs, specific frameworks, or a specific language.

## Submission form (every field they ask for)

Not stated. No submission-form page or field list was provided in the fetched content — only the problem statement and dataset docs. Do not fabricate form fields (project name, team members, video link, pitch deck, etc.) — these are unconfirmed.

## Judging criteria (and any stated obvious-vs-creative guidance)

Two sources conflict:
- **Dataset docs (governs for the technical task)**: scoring formula given for self-eval — "Final score = 50% end-to-end (defects caught all the way through) + 30% Stage-1 macro-F1 + 20% Stage-3 defect-F1. `NEEDS_REVIEW` handling is reported as a separate reliability axis." Explicitly caveated: "It is not the final assessment and does not cover every part of a good solution."
- **Marketing page**: "pitch live to senior engineering executives" — implies a live-pitch judging component with no stated rubric.

No overall competition rubric (e.g., weighting of code quality, presentation, business viability) is stated anywhere. Guidance given: "Accuracy means identifying the right requests and the right discrepancies without creating false alarms." Advanced-stage work ("harder, more realistic sample data") is explicitly where "you can stand out" — i.e., basic classify/extract/compare is table stakes, not differentiating.

## Prizes

"Compete for RM 9,000 in cash prizes." No breakdown by place stated.

## Intellectual property

Not stated. No IP clause appears anywhere in the fetched pages or documents.

## What this means for this entry

- The self-eval score formula is real and gameable-in-a-good-way: prioritize Stage-1 classification F1 and end-to-end defect detection over polish — that's 80% of the given metric.
- Basic capability (JSON/plain-text classify+compare) is the floor everyone will clear; judges are told the advanced stage (PDF/Word, scanned OCR, messy labels, reliability/review flow) is the differentiator — build that if time allows, don't gold-plate the basic path.
- `NEEDS_REVIEW` / human-in-the-loop is scored as a **separate axis**, not folded into accuracy — a system that never emits `NEEDS_REVIEW` is explicitly penalized on reliability even if accuracy is high. Implement it for real cases, not as a catch-all.
- No tool (including me) can produce: the live pitch to executives, any competition account/registration, the actual submission form (fields unknown), a demo video if one is required, or team formation/eligibility proof. These need direct action from you/your team.
- Dates are unknown — get the actual deadline before planning a schedule; "four days" is marketing color, not a locked timeline.
- IP terms are unstated — don't assume you retain rights or that the organizers claim them; get this in writing before treating the code as reusable post-hackathon.
- The submission form fields are completely unknown — don't build assets (video, pitch deck) blind; confirm the form first or you risk wasted work on the wrong format.
- Field-label normalization (SI vs BL wording mismatches) is called out explicitly as a trap — build alignment-by-meaning, not by exact header string, from the start; this will be tested in the sample data.
- "No mismatch detected" is the exact required output string when all 7 fields match — match it verbatim if you want to pass any string-based grading, though the given scoring is F1-based, not literal-string matching.