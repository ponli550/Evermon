# Submission form answers

Written by hand from the project's own docs (`README.md`, `docs/PITCH.md`,
`docs/BRIEF.md`) — not run through `hackager submission` (that's an LLM
wrapper; this didn't need one). Update here as more form fields get
confirmed (see `docs/RULES.md` for what's still unstated).

## Project Description / Summary (≤150 words)

Evermon (built by team DevSelf) reads a shipping-documentation inbox and
decides what each email needs: classify it, and for the ones asking to
check a Shipping Instruction against a draft Bill of Lading, compare seven
fields — shipper, consignee, notify party, ports, container count, gross
weight — by meaning, not header text, since the two documents never use
the same wording. When it can't decide (a wrong document type, an
unreadable scan, a blank required field, or a missing attachment) it
escalates to a person with one of four stated reasons instead of guessing.
Built in stdlib Python only: no network calls, no database, no LLM in the
decision path. Verified against the organisers' 520-email dataset and
their own grader: 1.0000 across classification, comparison, and escalation
reliability. A live-triage terminal dashboard demonstrates the same
pipeline processing emails as they arrive.

(138 words)

## Live Prototype / Demo URL

**https://evermon-demo.nazrijz336.workers.dev**

This is `web-demo/`, a Cloudflare Worker (static assets + client-side
TypeScript) — not the graded pipeline itself, which is a stdlib CLI with no
UI and nothing to host. It lets a visitor watch the real 520-email dataset
triage live (an animated "email arrives → classifies → compares" flow) and
edit SI/BL field values to test the comparison rules in-browser. Those
rules are a hand-ported, parity-verified copy of `dock/fields.py`'s value
comparison; all the classification/extraction/escalation results shown are
precomputed by the actual Python pipeline at build time
(`web-demo/scripts/export_dataset.py`), not reimplemented or guessed. See
`web-demo/README.md` for what's real about it and what isn't.
