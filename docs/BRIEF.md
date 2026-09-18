```markdown
## Idea

**PROPOSED** — the manifest's `one_liner` is empty, so this idea is not yet owned by the entrant; confirm or replace before building further. Build "Dock" — an automated shipping-document triage pipeline that reads raw email JSON + attachments, classifies each into `BL_COMPARISON`/`SI_REQUEST`/`INVOICE_QUERY`/`GENERAL`/`SPAM`, extracts the 7 comparable fields from SI/BL pairs by meaning (not header string), flags discrepancies, and escalates to `NEEDS_REVIEW` with a stated reason instead of guessing when data is missing, unreadable, or ambiguous.

## Track and why

`agent` — the core deliverable is an autonomous decision pipeline (classify → extract → compare → escalate) operating on unstructured inbound documents with no human in the loop except the explicit escalation path. Not `gen-ai`: an LLM is optional/advanced-stage only (OCR/vision for scanned PDFs), not the mechanism of the base solution.

## Hard requirements this must satisfy

- **Runs against provided dataset via `loader.py`** — CLI entrypoint calls `Inbox("data")` pointed at `docs/reference/sdoc-hackathon-bundle/inbox`, no server dependency required for the baseline path.
- **No DB/setup needed, stdlib works** — Python 3.11 stdlib only for the baseline `.txt` path; no external services at runtime.
- **Output matches `sample_submission.json` shape** — one JSON object keyed by `email_id`, every email present, fields `category`, and for `BL_COMPARISON`: `status`, `has_defect`, `defect_fields`, `review_reason`.
- **"No mismatch detected" exact string** — emitted verbatim when all 7 fields match, in case grading does literal comparison.
- **Field-label alignment by meaning** — a normalization map (e.g. "Port of Loading" == "Load Port") resolved before comparison, not exact-string keyed.
- **`NEEDS_REVIEW` is a real, reasoned path** — reasons restricted to `wrong_doc_type`, `missing_attachment`, `unreadable`, `missing_value`; never used as a silent catch-all, since it's scored as a separate reliability axis.
- **License** — repo already has `LICENSE`; no change needed unless license type is unconfirmed (check it explicitly).
- **README** — fill in one-liner, problem, how-it-works, and local run command (`python -m dock.cli --data docs/reference/sdoc-hackathon-bundle`).
- **Video/pitch** — not stated as a submission requirement in RULES.md; do not build assets blind. Flag to user before spending time on it.

## Bar for 'creative'

- Obvious: classify JSON emails with plain-text attachments, exact-header field matching, binary match/mismatch only.
- Creative: label-alignment-by-meaning across SI/BL vocabulary drift (explicitly the stated "trap"); PDF/Word attachment parsing with table extraction; scanned/image-only PDF handling via OCR; reasoned `NEEDS_REVIEW` triage instead of blanket pass/fail; handling messy/misleading-subject emails and missing attachments without crashing or false-flagging.

## Spec

- **Stack**: Python 3.11 (stdlib: `json`, `re`, `dataclasses`, `argparse`, `pathlib`). No network calls, no LLM calls anywhere in the base pipeline or tests. Optional advanced stage (PDF/OCR) isolated behind a separate module/flag, not required to pass tests.
- **Components**:
  - `dock/loader.py` — thin wrapper around provided `loader.py`, yields `(email_id, email_json, attachments)`.
  - `dock/classify.py` — rule-based classifier (keyword/subject/attachment-presence heuristics) → one of the 5 categories.
  - `dock/extract.py` — parses SI/BL plain-text attachments into 7 fields using a label-synonym map (`FIELD_ALIASES: dict[str, list[str]]`).
  - `dock/compare.py` — pairwise field diff, returns `status`, `has_defect`, `defect_fields`.
  - `dock/review.py` — decides `NEEDS_REVIEW` + `review_reason` when extraction/comparison can't proceed confidently.
  - `dock/cli.py` — `python -m dock.cli --data <dir> --out submission.json`.
- **No screens** — this is a CLI/batch tool, no UI.
- **Persistence** — none; stateless, reads inbox dir, writes one output JSON file per run.
- **Tests** (`tests/`, pytest, deterministic, no network/LLM):
  - `test_classify.py` — fixed sample emails → expected category, including a `SPAM` and a `GENERAL` case.
  - `test_extract.py` — SI/BL pair with mismatched header labels → correct field alignment.
  - `test_compare.py` — all-match case emits `"No mismatch detected"` verbatim; single-field mismatch flags correct `defect_fields`.
  - `test_review.py` — missing attachment / unreadable file / missing value each produce the correct `review_reason`, never silently pass.
  - `test_cli_e2e.py` — runs CLI against a small fixture subset of the real dataset, asserts output keys cover every input `email_id`.

## Done means

- [ ] `python -m dock.cli --data docs/reference/sdoc-hackathon-bundle --out submission.json` exits 0
- [ ] `submission.json` exists, is valid JSON, and has one key per file in `docs/reference/sdoc-hackathon-bundle/inbox/`
- [ ] `pytest tests/` exits 0
- [ ] `score_cli.py submission.json` (provided tool) runs without error against the generated file
- [ ] `README.md` has non-empty one-liner, problem, how-it-works, and a copy-pasteable run command
- [ ] `LICENSE` file present (already true — confirm content matches intended license)
- [ ] No file under `dock/` or `tests/` imports `requests`, `openai`, `anthropic`, or any network/LLM SDK

## Out of scope

- Live pitch deck / video — form and requirement unconfirmed, do not build blind.
- Any web UI, dashboard, or server beyond the optional Docker convenience path already documented in the dataset bundle.
- Database or persistent storage layer — not needed, dataset is file-based and static.
- LLM/vision integration in the required path — optional advanced-stage only, must not be load-bearing for base scoring.
- Multi-tenant/auth/user-account concerns — irrelevant to a single-batch CLI tool.
- Guessing submission-form fields, deadlines, or IP terms — all explicitly unstated in RULES.md; surface to user, don't fabricate.

## Manifest

```json
{
  "name": "AverisMonash2026",
  "one_liner": "PROPOSED: Dock — an agent pipeline that classifies inbound shipping emails, aligns SI/BL fields by meaning, flags discrepancies, and escalates to human review instead of guessing.",
  "problem": "Shipping ops teams manually read inbound emails and compare SI/BL documents field-by-field to catch discrepancies before cargo moves; this is slow, error-prone, and doesn't scale with volume or messy real-world document formats.",
  "market": "Freight forwarders, shipping lines, and logistics back-offices handling high-volume SI/BL document verification.",
  "track": "agent",
  "source": "",
  "demo": "",
  "status": "draft",
  "event": "https://averisxmonashhackathon2026.my/"
}
```
```