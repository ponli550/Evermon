## Hard requirements

| requirement | met? | evidence |
|---|---|---|
| Runs via `loader.py`, no server dependency | yes | `dock/sources.py` imports bundle loader; README run command matches `verify` runs |
| stdlib only, no network/LLM | yes | `verify` typecheck/lint/format all pass; README claims stdlib-only; no import check output shown but no `requests`/`openai` in `git ls-files` module list |
| Output matches `sample_submission.json` shape, one key per email | yes | verify score run reports 520 emails scored; `score_cli.py` ran without error |
| `"No mismatch detected"` verbatim | yes | README states it, `dock/compare.py` cited as owner; not independently grepped here — trust file exists, wording unverified by me |
| Field alignment by meaning | yes | `dock/fields.py` FIELD_ALIASES described in README with concrete examples |
| `NEEDS_REVIEW` real path, 4 reasons, not catch-all | yes | verify score output: 20/20 gold escalations, 5/5 per reason |
| License present | yes | `LICENSE` in `git ls-files`; README flags copyright holder is still a placeholder |
| README with one-liner/problem/how-it-works/run command | yes | README.md content shown has all sections |
| Tests pass | yes | `verify`: `test_passes: true`, 129 tests |
| `score_cli.py` runs without error | yes | `verify`: `score_passes: true`, FINAL SCORE 1.0000 |
| No network/LLM SDK imports in `dock/`/`tests/` | partly | asserted in README, not directly grepped in this review — verify it with `grep -rE "import (requests|openai|anthropic)" dock tests` before submitting |

## Judging criteria

- **Accuracy (classify+compare, no false alarms)**: Self-eval score is 1.0000, but that score was produced by the entry's own copy of `score_cli.py` against a bundle that (per README) ships no ground truth — this number is unverifiable by anyone outside the team. Improve: get an independent judge-side run, or stop quoting "1.0000" as if it's audited when it's self-graded.
- **Reliability / escalation as separate axis**: Genuinely handled — 20/20 gold escalations with correct reason precedence, and the README documents the false-positive trap (91 emails) they caught and fixed. Strongest part of the submission.
- **Creative/advanced stage**: PDF/xlsx/docx parsing done in stdlib, cross-format SI/BL pairs handled, but explicitly no OCR/vision — scanned PDFs just escalate. That's the correct, honest floor, not the differentiator RULES.md says to chase; if time remains, OCR is the single highest-leverage addition.
- **Code quality / rigor**: mypy strict + ruff + 129 tests all green. Nothing to improve here that would move a judge's opinion.
- **Presentation / pitch**: `docs/PITCH.md` exists but its content isn't shown here — cannot assess. RULES.md implies a live pitch to executives with unstated rubric; this is the biggest unaddressed criterion.

## Blocking gaps

- **Self-graded 1.0000 is a credibility risk, not a strength.** README says "the grader is not in this repo; it arrives with an answer key." If judges score independently and get a different number, the gap between claimed and actual score reads as either a hackathon norm (fine) or misleading (bad) depending entirely on how RULES.md's self-eval framing is actually enforced by organizers — unconfirmed here.
- **`watch/` directory ships a live-triage demo outside the graded pipeline.** README says it doesn't affect `submission.json`, but if a judge runs `pytest tests/` or lints the whole repo and `watch/` has its own Go binaries/build artifacts not covered by `.gitignore`, that's noise in the submission a judge has to mentally discount. Confirm `watch/` is clearly out-of-band in any repo-level README a judge reads first.
- **LICENSE has a placeholder copyright holder.** Cosmetic, but it's the kind of "we didn't finish" signal a nitpicking judge flags.
- **No submission form, deadline, or IP terms confirmed anywhere.** Not a code problem, but if the actual competition submission process requires something not in this repo (video, specific file, registration), none of that exists yet — this is a "you," not "code," gap, and it's the single most likely thing to actually disqualify or exclude the entry regardless of code quality.

## Nice-to-have

- OCR/vision fallback for scanned PDFs (explicitly the stated differentiator).
- Independent/third-party verification of the 1.0000 score before quoting it in a pitch.
- Fix the LICENSE placeholder copyright line.
- Confirm `docs/PITCH.md` content actually matches what RULES.md's live-pitch expectation implies — not reviewed here since not shown.