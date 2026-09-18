## Hard requirements

| requirement | met? | evidence |
|---|---|---|
| Runs via `loader.py`, no server dep | yes | `dock/sources.py` imports bundle's own `Inbox`, README confirms |
| stdlib only, no network/LLM | yes | `git ls-files` shows no requests/openai/anthropic imports; README states it, `verify` shows tests pass |
| CLI: `python -m dock.cli --data <dir> --out submission.json` exits 0 | partly | README shows this exact command and a sample run; no fresh exit-code check in `verify` output — only pytest was run |
| `submission.json` one key per inbox email, valid JSON | not visible | not generated/checked in the `verify` block; README claims 520/520 but that's self-reported, not re-verified here |
| Output shape matches `sample_submission.json` (`category`, `status`, `has_defect`, `defect_fields`, `review_reason`) | partly | `dock/compare.py`, `dock/review.py` exist and README describes the fields; no diff against the actual `sample_submission.json` shown |
| `"No mismatch detected"` verbatim | yes | README states it and `test_compare.py` (per BRIEF spec) asserts it — but see caveat below |
| Field alignment by meaning, not header string | yes | `dock/fields.py` (`FIELD_ALIASES`), README documents UN/LOCODE stripping and party-name-only comparison |
| `NEEDS_REVIEW` real, reasoned, not catch-all | yes | README: all 20 designed escalation cases land on correct reason |
| `pytest tests/` exits 0 | yes | `verify` block: `test_passes: true`, 129 tests pass |
| `score_cli.py submission.json` runs without error | **no** | README says outright: "the bundle does **not** include the `score_cli.py`". This is a stated Done-criterion that cannot be met — not your fault, but it's unmet as written |
| README non-empty one-liner/problem/how-it-works/run command | yes | `README.md` content shown, all sections present |
| `LICENSE` present | partly | file exists, but README admits copyright holder line is still a placeholder |
| No `requests`/`openai`/`anthropic` imports under `dock/`/`tests/` | yes | consistent with `git ls-files` and README's explicit claim |

## Judging criteria

- **Stage-1 classification F1 (30%)** — Strong on paper (body-first, subject-as-tiebreaker) but the README itself flags 91 "please send BL" emails classified `GENERAL` as a live judgement call that could cost 91 emails if ground truth disagrees. Single biggest lever: re-examine that one bucket before submission, since it's the single largest concentration of risk in the scored metric.
- **End-to-end defect detection (50%)** — Unmeasured. No ground truth, no scorer available, so this is asserted, not proven. The improvement that matters most: get any accuracy signal — hand-label a subset of the 129 comparison emails yourself and spot-check — because right now "63 OK / 46 MISMATCH / 20 NEEDS_REVIEW" is just what the pipeline decided, not what's correct.
- **NEEDS_REVIEW reliability (separate axis)** — Best-covered part of the submission: real branches, stated reasons, correct precedence, all 20 designed cases land correctly. Nothing to improve here for the given corpus; risk is only in generalizing to unseen corpora.
- **Field-label-alignment trap (creative bar)** — Explicitly built for, with a harvested alias table and a documented decoy (`NET WEIGHT`). This is the strongest, most deliberate part of the entry.
- **Advanced stage (PDF/OCR/messy inputs)** — Partially built: `.xlsx`/`.docx`/text-layer PDF parsing works; scanned/image PDFs are explicitly not attempted (`NEEDS_REVIEW/unreadable`, no OCR). Honest and defensible, but it's also exactly where competitors doing OCR pull ahead on "creative" scoring — a fallback vision-LLM call (kept out of the required scoring path per BRIEF) would close this gap fastest if time remains.

## Blocking gaps

- **`score_cli.py` doesn't exist in the bundle.** A stated Done-criterion is literally unachievable — confirm with organizers whether self-eval is expected at all before losing time chasing it.
- **Zero verified accuracy.** Everything about defect detection and classification correctness is self-reported from the pipeline's own output, not checked against any ground truth. If judges run their own scorer, this is the single biggest unknown — the entry could look great in the README and still score poorly.
- **The 91-email `GENERAL` vs `BL_COMPARISON/missing_attachment` judgement call** — could tank Stage-1 F1 in one move; README already flags this as the top risk itself.
- **LICENSE placeholder copyright holder** — minor but if organizers check license validity literally, an unfilled placeholder can read as sloppy or incomplete.
- **No submission-form assets, dates, or IP terms confirmed** — not a code gap, but if the actual submission portal wants a video/deck and none exists because "rules unstated," that's a hard disqualifier regardless of code quality. This needs direct action from the team now, not more engineering.

## Nice-to-have

- OCR/vision fallback for the 5 scanned/corrupt PDFs (currently correctly `NEEDS_REVIEW/unreadable`, but zero-value-added vs. a differentiating advanced-stage feature).
- HTTP/docker loader path is unexercised — worth one smoke test since judges may run via Docker.
- Fix the LICENSE placeholder — five-minute fix, no reason to leave it.