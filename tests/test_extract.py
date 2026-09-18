"""Turning a rendered document into a document type and seven field values."""

from pathlib import Path

from dock.documents import render
from dock.extract import DocumentType, extract

BUNDLE = Path(__file__).resolve().parents[1] / "docs/reference/sdoc-hackathon-bundle"
ATT = BUNDLE / "attachments"


SI = """SHIPPING INSTRUCTION
========================================

Shipper/Exporter: APRIL FAR EAST (M) SDN BHD
  TOWER 2, AVENUE 5; 59200 KUALA LUMPUR, MALAYSIA
CONSIGNEE: MOORIM SP CO., LTD
  656, GANGNAM-DAERO; SEOUL, SOUTH KOREA
NOTIFY PARTY: UAB NOVAKOPA
Port of Loading: PORT KLANG (WESTPORT), MALAYSIA (MYPKG)
Discharge Port: CALLAO, PERU (PECLL)
No. of Containers or Packages: 1 x 40'HC
Gross Weight (KG): 21,577 KG
NET WEIGHT: _______ MTS
HS Code: 48025600
Freight: PREPAID
"""

BL = """BILL OF LADING (DRAFT)
========================================

SHIPPER: APRIL FAR EAST (M) SDN BHD
  TOWER 2, AVENUE 5; 59200 KUALA LUMPUR, MALAYSIA
Consignee (Non-Negotiable): MOORIM SP CO., LTD
Notify: UAB NOVAKOPA
Load Port: PORT KLANG (WESTPORT), MALAYSIA
POD: CALLAO, PERU
Container Count: 1 x 40'HC
Gross Wt (kgs): 21,577 KG
Bill of Lading No.: MEDUUD104332
Freight: PREPAID
"""


def test_the_two_documents_use_different_labels_for_the_same_seven_fields() -> None:
    si, bl = extract(SI), extract(BL)
    assert si.doc_type is DocumentType.SHIPPING_INSTRUCTION
    assert bl.doc_type is DocumentType.BILL_OF_LADING
    assert set(si.values) == set(bl.values)
    assert si.values["port_of_loading"] == "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)"
    assert bl.values["port_of_loading"] == "PORT KLANG (WESTPORT), MALAYSIA"
    assert si.values["gross_weight_kg"] == "21,577 KG"
    assert bl.values["gross_weight_kg"] == "21,577 KG"


def test_only_the_party_name_is_taken_not_the_address_block() -> None:
    """One document carries the address, the other does not. Comparing the block would
    flag every such pair as a defect."""
    assert extract(SI).values["consignee"] == "MOORIM SP CO., LTD"
    assert extract(BL).values["consignee"] == "MOORIM SP CO., LTD"


def test_the_net_weight_decoy_is_not_captured_as_gross_weight() -> None:
    assert extract(SI).values["gross_weight_kg"] == "21,577 KG"


def test_the_first_occurrence_of_a_field_wins() -> None:
    doc = extract("SHIPPING INSTRUCTION\nPOD: SINGAPORE\nPort of Discharge: LONDON\n")
    assert doc.values["port_of_discharge"] == "SINGAPORE"


def test_blank_placeholders_are_recorded_as_blank_not_as_a_value() -> None:
    doc = extract(
        "SHIPPING INSTRUCTION\n"
        "Port of Loading (POL): ____MT\n"
        "Port of Discharge (POD): TBA\n"
        "Gross Weight毛重(KGS): N/A\n"
    )
    assert doc.blank_fields == {"port_of_loading", "port_of_discharge", "gross_weight_kg"}
    assert "port_of_loading" not in doc.values


class TestDocumentType:
    def test_a_bill_of_lading_instruction_is_a_shipping_instruction(self) -> None:
        """The phrase contains 'BILL OF LADING' but the document is the SI."""
        doc = extract("BILL OF LADING INSTRUCTION\nShipper: ACME\n")
        assert doc.doc_type is DocumentType.SHIPPING_INSTRUCTION

    def test_packing_list_is_neither(self) -> None:
        assert extract("PACKING LIST\nShipper: ACME\n").doc_type is DocumentType.OTHER

    def test_certificate_of_origin_is_neither(self) -> None:
        assert extract("CERTIFICATE OF ORIGIN\nExporter: ACME\n").doc_type is DocumentType.OTHER

    def test_commercial_invoice_is_neither(self) -> None:
        assert extract("COMMERCIAL INVOICE\nSeller: ACME\n").doc_type is DocumentType.OTHER

    def test_the_heading_may_not_be_on_the_first_line(self) -> None:
        doc = extract("ASIA PACIFIC PAPERBOARD TRADING PTE LTD\n\nBILL OF LADING: 3154303911\n")
        assert doc.doc_type is DocumentType.BILL_OF_LADING


class TestAgainstTheRealCorpus:
    def test_all_seven_fields_come_out_of_a_real_text_pair(self) -> None:
        si = extract(render(ATT / "email_001_SI.txt"))
        bl = extract(render(ATT / "email_001_BL.txt"))
        assert not si.missing_fields and not bl.missing_fields
        assert si.values["container_count"] == "1 x 40'HC"
        assert bl.values["notify_party"] == "UAB NOVAKOPA"

    def test_all_seven_fields_come_out_of_a_real_pdf(self) -> None:
        doc = extract(render(ATT / "email_059_SI.pdf"))
        assert doc.doc_type is DocumentType.SHIPPING_INSTRUCTION
        assert not doc.missing_fields
        assert doc.values["port_of_loading"] == "BUATAN, INDONESIA"
        assert doc.values["gross_weight_kg"] == "131,322 KG"
        assert doc.values["container_count"] == "6 x 40'HC"

    def test_all_seven_fields_come_out_of_a_real_docx(self) -> None:
        doc = extract(render(ATT / "email_055_BL.docx"))
        assert doc.doc_type is DocumentType.BILL_OF_LADING
        assert not doc.missing_fields
        assert doc.values["consignee"] == "AL GURG STATIONERY LLC"
        assert doc.values["gross_weight_kg"] == "243,588"

    def test_all_seven_fields_come_out_of_a_real_xlsx(self) -> None:
        doc = extract(render(ATT / "email_005_BL.xlsx"))
        assert doc.doc_type is DocumentType.BILL_OF_LADING
        assert not doc.missing_fields

    def test_the_commercial_invoice_posing_as_a_bl_is_detected_by_content(self) -> None:
        """The file is named ..._BL.txt. Only its content gives it away."""
        doc = extract(render(ATT / "email_501_BL.txt"))
        assert doc.doc_type is DocumentType.OTHER
