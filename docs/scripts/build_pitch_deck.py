#!/usr/bin/env python3
"""Build docs/AverisMonash2026.pptx as a real designed deck, not the plain
python-pptx-default-template dump `hackager slides` produces.

Content is transcribed from docs/PITCH.md -- nothing invented here, only
laid out and chunked so no slide exceeds ~60 words (the same density
threshold `hackager`/`check_density.py`-style tooling flags). Colors reuse
the validated categorical/status palette already used in web-demo/ and
watch/'s dashboard, so the deck, the website, and the terminal panel read
as one system instead of three unrelated looks.

Run with the hackathon-manager venv (has python-pptx):
  /Users/irfanali/Projects/Hackathon/hackathon-manager/.venv/bin/python3 \\
    docs/scripts/build_pitch_deck.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parents[1] / "AverisMonash2026.pptx"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Same slots as web-demo/public/style.css and watch/'s dashboard palette
# (dataviz skill's validated default -- see web-demo/README.md).
NAVY = RGBColor(0x0D, 0x1B, 0x2A)  # deep surface, not in the ramp itself
BLUE = RGBColor(0x2A, 0x78, 0xD6)  # categorical slot 1
YELLOW = RGBColor(0xED, 0xA1, 0x00)  # categorical slot 4 / accent
GOOD = RGBColor(0x0C, 0xA3, 0x0C)  # status good
CRITICAL = RGBColor(0xD0, 0x3B, 0x3B)  # status critical
INK = RGBColor(0x0B, 0x0B, 0x0B)
INK_SECONDARY = RGBColor(0x52, 0x51, 0x4E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAGE_BG = RGBColor(0xF9, 0xF9, 0xF7)

FONT = "Helvetica Neue"
MARGIN = Inches(0.7)
CONTENT_W = SLIDE_W - Inches(1.4)

_slide_no = 0


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, color) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False


def textbox(slide, x, y, w, h):
    box = slide.shapes.add_textbox(x, y, w, h)
    box.text_frame.word_wrap = True
    return box


def set_run(p, text: str, size: int, color: RGBColor, bold: bool = False, font: str = FONT):
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font


def footer(slide, prs) -> None:
    global _slide_no
    _slide_no += 1
    rect(slide, 0, prs.slide_height - Inches(0.06), prs.slide_width, Inches(0.06), YELLOW)
    box = textbox(slide, MARGIN, prs.slide_height - Inches(0.42), Inches(8), Inches(0.3))
    set_run(
        box.text_frame.paragraphs[0],
        "Evermon — Averis × Monash Hackathon 2026",  # noqa: RUF001
        10,
        INK_SECONDARY,
    )
    num = textbox(
        slide,
        prs.slide_width - Inches(1.0),
        prs.slide_height - Inches(0.42),
        Inches(0.6),
        Inches(0.3),
    )
    p = num.text_frame.paragraphs[0]
    set_run(p, str(_slide_no), 10, BLUE, bold=True)
    p.alignment = PP_ALIGN.RIGHT


def title_slide(prs, kicker: str, title: str, subtitle: str):
    slide = blank(prs)
    rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY)
    rect(slide, 0, Inches(6.9), prs.slide_width, Inches(0.12), YELLOW)

    kick = textbox(slide, MARGIN, Inches(1.9), CONTENT_W, Inches(0.5))
    set_run(kick.text_frame.paragraphs[0], kicker.upper(), 16, YELLOW, bold=True)

    t = textbox(slide, MARGIN, Inches(2.5), CONTENT_W, Inches(1.6))
    set_run(t.text_frame.paragraphs[0], title, 54, WHITE, bold=True)

    s = textbox(slide, MARGIN, Inches(4.3), CONTENT_W, Inches(1.8))
    p = s.text_frame.paragraphs[0]
    set_run(p, subtitle, 20, RGBColor(0xC3, 0xC9, 0xD1))
    footer(slide, prs)
    return slide


def section_slide(prs, number: int, title: str, note: str = ""):
    slide = blank(prs)
    rect(slide, 0, 0, prs.slide_width, prs.slide_height, BLUE)

    num = textbox(slide, MARGIN, Inches(2.2), Inches(2.5), Inches(1.4))
    set_run(num.text_frame.paragraphs[0], f"{number:02d}", 80, YELLOW, bold=True)

    t = textbox(slide, MARGIN, Inches(3.5), CONTENT_W, Inches(1.3))
    set_run(t.text_frame.paragraphs[0], title, 40, WHITE, bold=True)

    if note:
        n = textbox(slide, MARGIN, Inches(4.7), CONTENT_W, Inches(0.8))
        set_run(n.text_frame.paragraphs[0], note, 18, RGBColor(0xE3, 0xEC, 0xFA))
    footer(slide, prs)
    return slide


def bullet_slide(prs, title: str, bullets: list[str], kicker: str = ""):
    slide = blank(prs)
    rect(slide, 0, 0, prs.slide_width, Inches(1.3), BLUE)
    if kicker:
        kb = textbox(slide, MARGIN, Inches(0.18), CONTENT_W, Inches(0.3))
        set_run(kb.text_frame.paragraphs[0], kicker.upper(), 12, YELLOW, bold=True)
    tb = textbox(slide, MARGIN, Inches(0.45) if kicker else Inches(0.3), CONTENT_W, Inches(0.8))
    set_run(tb.text_frame.paragraphs[0], title, 28, WHITE, bold=True)

    body = textbox(slide, MARGIN, Inches(1.7), CONTENT_W, Inches(5.0))
    tf = body.text_frame
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, f"▸  {b}", 18, INK)
        p.space_after = Pt(16)
    footer(slide, prs)
    return slide


def stat_slide(prs, title: str, stats: list[tuple[str, str, RGBColor]]):
    """A row of big numbers -- for the accuracy/reliability scoreboard."""
    slide = blank(prs)
    rect(slide, 0, 0, prs.slide_width, prs.slide_height, PAGE_BG)
    tb = textbox(slide, MARGIN, Inches(0.5), CONTENT_W, Inches(0.8))
    set_run(tb.text_frame.paragraphs[0], title, 28, INK, bold=True)

    n = len(stats)
    col_w = CONTENT_W / n
    for i, (value, label, color) in enumerate(stats):
        x = MARGIN + col_w * i
        vb = textbox(slide, x, Inches(2.3), col_w, Inches(1.4))
        p = vb.text_frame.paragraphs[0]
        set_run(p, value, 56, color, bold=True)
        p.alignment = PP_ALIGN.CENTER
        lb = textbox(slide, x, Inches(3.7), col_w, Inches(1.0))
        p2 = lb.text_frame.paragraphs[0]
        p2.text = label
        p2.font.size = Pt(15)
        p2.font.color.rgb = INK_SECONDARY
        p2.font.name = FONT
        p2.alignment = PP_ALIGN.CENTER
        p2.word_wrap = True
    footer(slide, prs)
    return slide


def closing_slide(prs, title: str, lines: list[str]):
    slide = blank(prs)
    rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY)
    rect(slide, 0, 0, prs.slide_width, Inches(0.12), YELLOW)
    tb = textbox(slide, MARGIN, Inches(2.3), CONTENT_W, Inches(1.2))
    set_run(tb.text_frame.paragraphs[0], title, 48, WHITE, bold=True)
    body = textbox(slide, MARGIN, Inches(3.7), CONTENT_W, Inches(2.5))
    tf = body.text_frame
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, line, 18, RGBColor(0xC3, 0xC9, 0xD1))
        p.space_after = Pt(10)
    footer(slide, prs)
    return slide


def build() -> None:
    prs = new_deck()

    title_slide(
        prs,
        kicker="Averis × Monash Hackathon 2026 — Team DevSelf",  # noqa: RUF001
        title="Evermon",
        subtitle=(
            "Reads a shipping-documentation inbox, compares SI against draft BL "
            "by meaning, escalates to a person with a stated reason instead of "
            "guessing."
        ),
    )

    section_slide(prs, 1, "The Problem")
    bullet_slide(
        prs,
        "Clerks manually cross-check SI vs BL",
        [
            "Seven fields, by hand: shipper, consignee, notify party, load/discharge port, container count, gross weight.",  # noqa: E501
            'Documents never use the same labels — "Port of Loading" vs "Load Port".',
            "A missed mismatch puts the wrong consignee on a negotiable shipping document.",
        ],
    )

    section_slide(prs, 2, "Why This Isn't a Wrapper")
    bullet_slide(
        prs,
        "Rule-based, not prompted",
        [
            "Alias-table field alignment (dock/fields.py) and four-reason escalation precedence (dock/review.py) are the product.",  # noqa: E501
            'An LLM given "compare these two documents" gets inconsistent field matching and no auditable policy.',  # noqa: E501
            "Escalation reasons are fixed, never model-improvised — that's the pitch that survives a technical judge's follow-up.",  # noqa: E501
        ],
    )

    section_slide(prs, 3, "Market — Who Pays")
    bullet_slide(
        prs,
        "Freight forwarders & shipping-line back offices",
        [
            "Buyer: the ops manager who owns error/rework cost and demurrage exposure — not the individual clerk.",  # noqa: E501
            "Real B2B wedge, but a crowded category — needs one sharp number, e.g. clerk-hours saved per 100 emails.",  # noqa: E501
        ],
    )

    section_slide(prs, 4, "Open-Source Strategy")
    bullet_slide(
        prs,
        "Ship the trust layer, keep the moat",
        [
            "Open: classification rules, alias table, escalation logic (dock/classify.py, fields.py, review.py) — auditability is the trust argument.",  # noqa: E501
            'Closed: document-parsing edge cases and any fine-tuned extraction — the maintenance moat, not "the loader".',  # noqa: E501
        ],
    )

    section_slide(prs, 5, "Live Demo")
    bullet_slide(
        prs,
        "Three steps, under two minutes",
        [
            "Classify: spam, invoice chase, and a real SI+draft-BL pair — sorted correctly in one pass.",  # noqa: E501
            'Relabelled fields ("Load Port" vs "Port of Loading") still align and flag a real mismatch.',  # noqa: E501
            "A missing/unreadable attachment escalates to NEEDS_REVIEW with the specific reason, not a guess.",  # noqa: E501
        ],
    )

    stat_slide(
        prs,
        "Verified against the organisers' own grader",
        [
            ("1.0000", "overall score — classification, comparison, escalation", BLUE),
            ("129", "deterministic tests — no network, no LLM", GOOD),
            ("46 / 46", "real defect emails caught, 20 / 20 correctly escalated", CRITICAL),
        ],
    )

    # --- Documentation appendix: docs/DOCUMENTATION.md, condensed -----------

    section_slide(prs, 6, "Technical Architecture")
    bullet_slide(
        prs,
        "Three parts, one shared core",
        [
            "dock/: classify -> extract -> compare -> escalate. Stdlib Python 3.11, the graded submission.",  # noqa: E501
            "watch/: Go CLI + terminal dashboard, reuses dock.pipeline.decide() live — not a second implementation.",  # noqa: E501
            "web-demo/: static Cloudflare Worker, a parity-verified TypeScript port of just the comparison rules.",  # noqa: E501
        ],
    )

    section_slide(prs, 7, "Implementation Details")
    bullet_slide(
        prs,
        "What actually makes it accurate",
        [
            "Classification reads the body first, not the subject — this corpus deliberately mislabels it.",  # noqa: E501
            "Field alignment is table-driven: an unrecognised label returns nothing, never a guess.",  # noqa: E501
            "No OCR, no vision model — scanned PDFs escalate correctly instead of inventing a value.",  # noqa: E501
        ],
    )

    section_slide(prs, 8, "Challenges Faced")
    bullet_slide(
        prs,
        "Two scoring incidents, one operational",
        [
            '91 "please send the BL" emails were first misclassified GENERAL — the scoreboard caught it.',  # noqa: E501
            "That fix alone spiked false escalations 20 -> 111, fixed with a narrower rule.",
            "A stray background daemon raced a live correction during testing — an operational gap.",  # noqa: E501
        ],
    )

    section_slide(prs, 9, "Future Roadmap")
    bullet_slide(
        prs,
        "What's next, and what's deliberately not built yet",
        [
            "An audited OCR/vision fallback for scanned PDFs, with a stated confidence and escalation on doubt.",  # noqa: E501
            "Push-based escalation (webhook/notification) instead of a file a person has to poll.",
            "A single-instance lock for the watcher daemon; exercising the untested Docker/HTTP loader path.",  # noqa: E501
        ],
    )

    closing_slide(
        prs,
        "Try it yourself",
        [
            "Live prototype: evermon-demo.nazrijz336.workers.dev",
            "Demo video: youtu.be/TE72CMXwmZ0",
            "Source: github.com/ponli550/Evermon",
            "Thank you.",
        ],
    )

    prs.save(str(OUT))
    print(f"{len(prs.slides)} slides -> {OUT}")


if __name__ == "__main__":
    build()
