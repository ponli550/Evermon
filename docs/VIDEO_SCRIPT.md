# Demo video script — 5 sections, ≤5:00

A script and shot list for a real recording, not a rendered/AI-narrated
video — `hackager demo`/`narrate` were deliberately skipped (real API
cost, and this is short enough to write and read straight). Once you've
actually recorded it, re-time `docs/demo.srt` against the real footage —
its timestamps here are *estimated* from a ~140 words/minute reading pace,
not measured.

Every command below is real and already verified in this repo — nothing
staged, nothing that only works on camera.

---

## 1. Quick Intro — 0:00–0:20 (20s)

**On screen:** title card or terminal with `cat README.md | head -5`.

**Say:**
> "We're team DevSelf, and this is Evermon — a pipeline that reads a shipping
> documentation inbox, checks Shipping Instructions against draft Bills of
> Lading, and tells you exactly what's wrong, or exactly why it can't
> decide."

## 2. The Problem — 0:20–1:05 (45s)

**On screen:** two real attachments side by side (e.g.
`docs/reference/sdoc-hackathon-bundle/attachments/email_013_SI.txt` and
`..._BL.txt`), or the README's problem section.

**Say:**
> "A shipping documentation clerk gets a mailbox full of noise — spam,
> invoice chases, broadcast notices — and buried in it, the emails that
> actually matter: 'here's the SI and the draft BL, please check.' Someone
> has to read two documents side by side and compare seven fields by hand.
> The documents never use the same words — one says 'Port of Loading,'
> the other says 'Load Port.' Miss a mismatch, and the wrong consignee
> ends up on a negotiable shipping document. That's the real cost this
> solves."

## 3. Tech Stack & Philosophy — 1:05–2:05 (60s)

**On screen:** `dock/` directory listing, or the module table from
`docs/DOCUMENTATION.md`; cut to `dock/fields.py`'s `FIELD_ALIASES` table and
`dock/review.py`'s precedence tuple while naming them.

**Say:**
> "The core pipeline is Python 3.11, standard library only — no database,
> no network calls, no LLM in the classify-compare-escalate decision.
> That's deliberate: alignment by meaning is table-driven, not fuzzy, and
> escalation is four precedence-ordered reasons, not a confidence score.
> An unrecognised label returns nothing rather than a guess, because a
> wrong match here is worse than a missed one.
>
> AI comes in exactly one place, on the cloud: when an email escalates
> because a field's blank, one headless Claude call checks whether the
> other document already states it, and only ever copies a value that's
> actually written down — never invents one.
>
> The live demo runs on a small Go CLI and terminal dashboard, same
> pipeline imported as a library. The hosted version is a Cloudflare
> Worker with the comparison rules ported to TypeScript, verified
> line-for-line against the Python original before shipping."

## 4. Live Demo — 2:05–4:30 (2:25)

**Commands to actually run on camera, in order:**

```bash
# 1. Batch run against the full 520-email dataset
python3 -m dock.cli --data docs/reference/sdoc-hackathon-bundle --out submission.json

# 2. Show one real defect being caught, explained
python3 -m dock.cli --data docs/reference/sdoc-hackathon-bundle --explain 2>&1 | grep email_013

# 3. Open the live dashboard
cd watch && ./watch-ctl start && ./watch-popup
#   then inside the panel: f  (feed sample emails), watch the board fill in

# 4. Point at one flagged card (email_013) -- side-by-side SI/BL, why it's flagged

# 5. Edit-and-resend: cursor on the flagged row, press e, fix the port in $EDITOR,
#    watch it resolve to "No mismatch detected" live

# 6. AI fix: cursor on a NEEDS_REVIEW (missing_value) row, press a --
#    claude checks the other document and resends a corrected copy live

# 7. Cut to the browser: https://evermon-demo.nazrijz336.workers.dev
```

**Say (over the batch run):**
> "One command classifies all 520 emails and writes the submission file —
> here's the summary: 220 comparison requests, 154 clean, 46 real
> mismatches, 20 escalated to a human."

**Say (over `--explain` / email_013):**
> "Here's one: same shipper, same consignee, same everything — except the
> port of discharge. SI says Mombasa, Kenya; the draft BL says Tuticorin,
> India. Every other field matches, which is exactly why this is a real
> defect and not noise."

**Say (over the dashboard):**
> "This is the same pipeline, live — watching an inbox, charting what's
> coming in, and surfacing exactly what needs a person and why, side by
> side, not just a flag."

**Say (over edit-and-resend):**
> "And this is what happens after someone fixes the flagged document — we
> resend it as a new email, and it re-triages clean, live."

**Say (over the AI fix):**
> "Same idea, but automatic: Claude reads both documents, finds the value
> stated on the other side, and only resends if it can actually prove the
> fix — otherwise it leaves it escalated, exactly as it should."

**On screen:** cut to https://evermon-demo.nazrijz336.workers.dev in a browser.

**Say (over the web demo, ~10s):**
> "We also shipped this as a hosted prototype, so anyone can try the same
> comparison rules themselves in a browser, no clone required."

## 5. Impact — 4:30–4:50 (20s)

**On screen:** `uv run pytest -q` passing, or the scoreboard numbers from
`README.md`.

**Say:**
> "129 deterministic tests. Against the organisers' own grader — which we
> don't ship, since it comes with the answer key — this scores 1.0000:
> perfect classification, perfect comparison, 20 out of 20 correctly
> escalated."

## Close — 4:50–5:00 (10s)

**Say:**
> "That's Evermon. Thanks for watching."

---

## Timing budget

| section | target | cumulative |
|---|---|---|
| Intro | 0:20 | 0:20 |
| Problem | 0:45 | 1:05 |
| Tech Stack & Philosophy | 1:00 | 2:05 |
| Live Demo (now 7 steps, incl. AI fix + web demo) | 2:25 | 4:30 |
| Impact | 0:20 | 4:50 |
| Close | 0:10 | 5:00 |

Still hits the cap exactly on paper, after trimming Impact's narration to
make room for the new AI-fix beat. In practice, budget a few seconds of
slack (natural pauses, a slower reader) by tightening the Live Demo
commentary first; it has the most room since a lot of that time is real
commands executing, not speech.
