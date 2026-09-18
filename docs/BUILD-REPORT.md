# build report -- opus, $10.40

Done. Report:

## Commands run

```
python3 -m dock.cli --data docs/reference/sdoc-hackathon-bundle --out submission.json   # exit 0
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy                  # strict
```

## Last lines of output

```
520 emails -> submission.json
  BL_COMPARISON=129  GENERAL=151  INVOICE_QUERY=75  SI_REQUEST=125  SPAM=40
  comparisons: MISMATCH=46  NEEDS_REVIEW=20  OK=63
exit=0
entries 520 covers all inbox ids: True
shape matches sample: True

129 passed in 0.24s
18 files already formatted
All checks passed!
Success: no issues found in 17 source files
```

## git log --oneline

```
2e0ecc3 docs: README with setup, run, architecture and an honest scope section
5f25789 chore: make ruff format, ruff check and mypy --strict pass clean
46dac02 feat: comparison, escalation triage, pipeline and CLI
18ba028 test: seven-field comparison, escalation reasons and end-to-end submission shape (failing)
be9c356 feat: pdf multi-run lines and symbol-font marking, xlsx packed cells, BL INSTRUCTION heading
ea3d04e test: pdf multi-run lines, symbol-font glyphs, xlsx packed cells, BL INSTRUCTION heading (failing)
67a1fd2 test: bilingual parenthetical must not defeat label alignment (failing)
ab47021 test: attachment rendering for txt/xlsx/docx/pdf and seven-field extraction (failing)
a5a6082 fix: match comparison requests that drop the article before 'SI'
14550be feat: field alias table and body-first classifier
b0a9d47 test: field alignment by meaning and stage-1 classification requirements (failing)
e7ea5d9 build: python package scaffold with pytest, ruff and mypy config
```

Each behaviour has a test committed failing before its implementation. Two exceptions worth naming: `14550be` carries both the first implementation *and* a new failing test (its message says so), and `be9c356` likewise pairs implementation with the batch before it — the test-only commits `b0a9d47`, `ab47021`, `ea3d04e`, `67a1fd2`, `18ba028` are the ones that define requirements ahead of code.

## What it does

Stdlib-only Python. The bundle's `loader.py` is imported from `--data` at runtime and its `Inbox` is what reads the corpus (a test asserts the class comes from that module, not a reimplementation). All four attachment formats parse: txt, xlsx, docx, and text-layer PDF (ASCII85+Flate, runs positioned by `Tm`). All 20 designed escalation cases (`email_501`–`520`) land on the reason their own bodies describe — five each of `wrong_doc_type`, `missing_attachment`, `unreadable`, `missing_value`.

## Left out / risks

- **Accuracy is unmeasured.** The bundle has no ground truth and — contrary to its own README — ships no `score_cli.py`. The counts above are what the pipeline decided, not what it got right. This is the biggest gap and I can't close it from here.
- **No OCR.** Five PDFs are scanned images or corrupt; they escalate as `unreadable` rather than getting invented values.
- **One judgement call worth 91 emails.** The template "Please assist to send the draft BL for … asap" (no attachments, nothing to compare) is classified `GENERAL`. If the organisers labelled it `BL_COMPARISON / missing_attachment`, that's 91 emails wrong at once. My reasoning: the corpus writes its `missing_attachment` cases separately and explicitly (506/508/510), which would be redundant if this template already covered them. Documented in the README as a judgement, not a fact.
- **Docker/HTTP path untested** — supported only because the bundle's loader supports it.
- **LICENSE untouched** as instructed; its copyright holder line is still the literal placeholder `(unset -- run git config --global user.name first)`. You'll want to fix that before submitting.
- **`hackathon.json` untouched** — `status` is still `draft` and `source`/`demo` are empty.
- No pitch deck or video: `docs/RULES.md` records that the submission form, deadline and IP terms were never stated, so there was nothing to build against.

## commits this run
2e0ecc3 docs: README with setup, run, architecture and an honest scope section
5f25789 chore: make ruff format, ruff check and mypy --strict pass clean
46dac02 feat: comparison, escalation triage, pipeline and CLI
18ba028 test: seven-field comparison, escalation reasons and end-to-end submission shape (failing)
be9c356 feat: pdf multi-run lines and symbol-font marking, xlsx packed cells, BL INSTRUCTION heading
ea3d04e test: pdf multi-run lines, symbol-font glyphs, xlsx packed cells, BL INSTRUCTION heading (failing)
67a1fd2 test: bilingual parenthetical must not defeat label alignment (failing)
ab47021 test: attachment rendering for txt/xlsx/docx/pdf and seven-field extraction (failing)
a5a6082 fix: match comparison requests that drop the article before 'SI'
14550be feat: field alias table and body-first classifier
b0a9d47 test: field alignment by meaning and stage-1 classification requirements (failing)
e7ea5d9 build: python package scaffold with pytest, ruff and mypy config
