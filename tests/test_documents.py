"""Attachment readers.

Every format is rendered down to the same canonical shape - one "Label: value" line
per field, with continuation lines indented - so that exactly one parser sees documents
regardless of whether they arrived as text, a spreadsheet, a Word table or a PDF.

A reader that cannot produce text must say so loudly (Unreadable), never return
something empty and let the comparison silently pass.
"""

from pathlib import Path

import pytest

from dock.documents import Unreadable, render

BUNDLE = Path(__file__).resolve().parents[1] / "docs/reference/sdoc-hackathon-bundle"
ATT = BUNDLE / "attachments"


def test_plain_text_is_passed_through() -> None:
    text = render(ATT / "email_001_SI.txt")
    assert "Port of Loading: PORT KLANG (WESTPORT), MALAYSIA (MYPKG)" in text


def test_xlsx_two_column_sheet_becomes_label_value_lines() -> None:
    text = render(ATT / "email_005_BL.xlsx")
    assert "BILL OF LADING" in text
    assert "Shipper (Principal or Seller): ASIA PACIFIC PAPERBOARD TRADING PTE LTD" in text


def test_docx_table_rows_become_label_value_lines() -> None:
    text = render(ATT / "email_055_BL.docx")
    assert "BILL OF LADING (DRAFT)" in text
    assert "Consignee (收货人): AL GURG STATIONERY LLC" in text
    assert "Total Containers (箱数): 12 x 20'FCL" in text


def test_docx_paragraphs_in_one_cell_are_separated() -> None:
    """Word keeps the address on its own paragraphs; joining them blind fuses words."""
    text = render(ATT / "email_055_BL.docx")
    assert "APRIL FINE PAPER TRADINGON BEHALF" not in text


def test_pdf_two_column_layout_becomes_label_value_lines() -> None:
    text = render(ATT / "email_059_SI.pdf")
    assert "BILL OF LADING INSTRUCTION" in text
    assert "POL: BUATAN, INDONESIA" in text
    assert "Port of Discharge (POD): FREMANTLE, AUSTRALIA" in text
    assert "No. of Containers: 6 x 40'HC" in text


def test_pdf_escaped_parentheses_are_unescaped() -> None:
    text = render(ATT / "email_059_SI.pdf")
    assert "PACIFIC OFFICE (M) SDN BHD" in text
    assert "\\(" not in text


def test_pdf_container_manifest_rows_are_not_read_as_fields() -> None:
    """The per-container table repeats a GROSS WEIGHT column; reading it would give
    one container's weight instead of the shipment total."""
    text = render(ATT / "email_059_SI.pdf")
    assert "GROSS WEIGHT (KG): 21,887" not in text
    assert "TOTAL Gross Wt (kgs): 131,322 KG" in text


def test_pdf_runs_sharing_one_position_form_one_line() -> None:
    """A bilingual label is drawn as three runs under a single Tm - label, CJK gloss in a
    symbol font, then the rest. Reading only the first run loses the value entirely."""
    text = render(ATT / "email_160_SI.pdf")
    line = next(ln for ln in text.splitlines() if ln.startswith("TOTAL Gross Weight"))
    assert line.endswith("(KGS): 23,702 KG")


def test_pdf_symbol_font_glyphs_are_marked_undecodable() -> None:
    """ZapfDingbats carries no text encoding; its bytes are glyph ids, not characters.
    They are replaced rather than passed off as latin text."""
    text = render(ATT / "email_160_SI.pdf")
    assert "�" in text
    assert "Weightnn(KGS)" not in text


def test_xlsx_pipe_separated_cell_becomes_continuation_lines() -> None:
    """The workbook packs the address into the same cell as the party name."""
    text = render(ATT / "email_005_BL.xlsx")
    assert "CONSIGNEE: BALL & DOGGETT AUSTRALIA PTY LTD" in text
    assert " | " not in text


@pytest.mark.parametrize("name", ["email_512_SI.pdf", "email_513_BL.pdf"])
def test_image_only_pdf_is_unreadable(name: str) -> None:
    """Scanned pages carry no text layer. Without OCR this pipeline must escalate,
    not invent values."""
    with pytest.raises(Unreadable):
        render(ATT / name)


@pytest.mark.parametrize("name", ["email_511_BL.pdf", "email_515_BL.pdf"])
def test_corrupt_pdf_is_unreadable(name: str) -> None:
    with pytest.raises(Unreadable):
        render(ATT / name)


def test_unknown_extension_is_unreadable(tmp_path: Path) -> None:
    target = tmp_path / "mystery.rtf"
    target.write_bytes(b"{\\rtf1}")
    with pytest.raises(Unreadable):
        render(target)


def test_missing_file_is_unreadable(tmp_path: Path) -> None:
    with pytest.raises(Unreadable):
        render(tmp_path / "nope.txt")
