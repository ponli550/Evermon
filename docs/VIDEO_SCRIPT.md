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

## 3. Tech Stack — 1:05–1:40 (35s)

**On screen:** `dock/` directory listing, or the module table from
`docs/DOCUMENTATION.md`.

**Say:**
> "The pipeline is Python 3.11, standard library only — no database, no
> network calls, no LLM in the decision path. Classification, field
> alignment, and comparison are rule-based and auditable, not a prompt.
> For the live demo, we built a small Go CLI and a terminal dashboard on
> top — same pipeline, imported as a library, watching an inbox in real
> time instead of running once as a batch."

## 4. Live Demo — 1:40–4:10 (2:30)

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
> "And this is what happens after someone reads the escalation and fixes
> the document — we resend it as a new email, and it re-triages clean, in
> real time."

## 5. Impact — 4:10–4:50 (40s)

**On screen:** `uv run pytest -q` passing, or the scoreboard numbers from
`README.md`.

**Say:**
> "129 tests, deterministic, no network or LLM anywhere in the graded
> path. Against the organisers' own grader — which we don't ship, since it
> comes with the answer key — this scores 1.0000: perfect classification,
> perfect comparison, and 20 out of 20 on the reliability axis, the one
> that actually measures whether 'needs review' means something or is
> just a shrug."

## Close — 4:50–5:00 (10s)

**Say:**
> "That's Evermon. Thanks for watching."

---

## Timing budget

| section | target | cumulative |
|---|---|---|
| Intro | 0:20 | 0:20 |
| Problem | 0:45 | 1:05 |
| Tech Stack | 0:35 | 1:40 |
| Live Demo | 2:30 | 4:10 |
| Impact | 0:40 | 4:50 |
| Close | 0:10 | 5:00 |

Total narration is ~420 words outside the demo section, comfortably inside
a 5-minute cap even accounting for pauses during the live commands.
