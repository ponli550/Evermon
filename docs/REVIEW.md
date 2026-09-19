## Hard requirements

| requirement | met? | evidence |
|---|---|---|
| Runs via `loader.py`, no server dep | yes | `dock/sources.py` imports bundle loader; README run command; verify log shows tests pass |
| Stdlib only, no network/LLM | yes | README states Python 3.11 stdlib; `ruff`/`mypy` pass clean per verify log; no `requests`/`openai` in `git ls-files` module list |
| Output matches `sample_submission.json` shape | yes (claimed) | README: "one entry per email_id" — not independently verified here, no `submission.json` in `git ls-files` |
| `"No mismatch detected"` exact string | yes | README states it verbatim; `dock/compare.py` presumably implements it — not opened to confirm |
| Field-label alignment by meaning | yes | `dock/fields.py` FIELD_ALIASES described in README with concrete examples (locode stripping, party-name-only) |
| `NEEDS_REVIEW` real, reasoned, 4 causes | yes | README + `dock/review.py`; verify shows tests pass covering this |
| License present | yes | `LICENSE` in `git ls-files`; README admits copyright holder line is still placeholder |
| README with one-liner/problem/how-it-works/run cmd | yes | README file shown, all sections present |
| pytest exits 0 | yes | verify log: `test_passes: true`, 129 tests |
| `score_cli.py submission.json` runs without error | **not visible** | not in `git ls-files`, not in verify checks — brief requires this as a "Done means" item and it is untested/unconfirmed |
| No `dock/`/`tests/` imports of network/LLM SDKs | yes | mypy/ruff clean, no such packages in dependency files shown |

## Judging criteria

- **Accuracy (classify+compare)**: Strong on paper — README claims 1.0000 self-graded score — but that score comes from the entry's *own* grader reasoning, not the organizers' held-out `score_cli.py`, which the repo admits it doesn't have. → Get the actual `score_cli.py` from the bundle and run it before submission; a self-reported 1.0000 with no independent check will read as unverifiable to a judge.
- **Reliability / NEEDS_REVIEW axis**: Well-designed — 20/20 gold escalations hit, explicitly not a catch-all, precedence-ordered reasons. This is the strongest part of the submission. → Nothing needed; if anything, cite the escalation-precision regression story (111→20) in the pitch, it's the best evidence of engineering rigor.
- **Advanced/creative stage**: PDF/xlsx/docx parsing done with stdlib (genuinely hard, genuinely differentiating), but OCR/scanned-PDF explicitly not attempted (5 emails just return `unreadable`). → If time remains, a minimal OCR fallback (even a bad one) would close this gap; otherwise it's an honest, defensible gap, not a blocker.
- **Code quality / correctness signals**: Tests, lint, format, typecheck all green per verify log — clean. → Nothing to improve; don't over-invest further here, time is better spent on the pitch/README polish below.
- **Presentation/pitch**: Unknown — no pitch deck/video, and RULES.md says "pitch live to senior engineering executives" is part of judging with no rubric. → This is the actual gap right now: prepare a 3–5 min narrative around the classify→escalate pipeline and the "91-email reclassification" war story, since that's your best concrete engineering-judgment anecdote.

## Blocking gaps

- **`score_cli.py` never run.** The brief's own "Done means" checklist requires it; verify.json doesn't cover it. If judges run it and it errors or the output shape is subtly wrong, you find out live instead of now. Run it before submission.
- **LICENSE has a placeholder copyright holder.** Cosmetic but visible; a judge who opens LICENSE and sees a placeholder reads it as unfinished.
- **No submission-form completed** (not this repo's problem, but RULES.md flags form fields/deadline/IP as entirely unstated) — confirm these exist and are filed; a perfect repo with no submission is a zero.
- **Live-pitch component is unaddressed.** RULES.md says judging includes pitching to executives; nothing in the repo prepares for that.

## Nice-to-have

- Fix the LICENSE placeholder — five-minute fix, removes an obvious "we didn't finish" signal.
- Confirm `--data <docker-url>` path actually works — README admits it's untested; low priority since not required.
- `watch/` demo is a good pitch prop (live triage) — make sure it's runnable standalone for the live-pitch, since a batch CLI is hard to demo live per its own README admission.