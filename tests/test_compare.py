"""Stage 3: the seven-field diff, and the exact wording of its verdict."""

from dock.compare import NO_MISMATCH, compare
from dock.extract import Document, DocumentType


def doc(kind: DocumentType, **values: str) -> Document:
    return Document(doc_type=kind, values=dict(values))


BASE = {
    "shipper": "APRIL FAR EAST (M) SDN BHD",
    "consignee": "MOORIM SP CO., LTD",
    "notify_party": "UAB NOVAKOPA",
    "port_of_loading": "PORT KLANG (WESTPORT), MALAYSIA",
    "port_of_discharge": "CALLAO, PERU",
    "container_count": "1 x 40'HC",
    "gross_weight_kg": "21,577 KG",
}


def si(**overrides: str) -> Document:
    return doc(DocumentType.SHIPPING_INSTRUCTION, **{**BASE, **overrides})


def bl(**overrides: str) -> Document:
    return doc(DocumentType.BILL_OF_LADING, **{**BASE, **overrides})


def test_a_clean_pair_reports_the_exact_required_wording() -> None:
    result = compare(si(), bl())
    assert result.status == "OK"
    assert result.has_defect is False
    assert result.defect_fields == []
    assert result.summary == "No mismatch detected"
    assert NO_MISMATCH == "No mismatch detected"


def test_one_differing_field_is_named_and_only_that_field() -> None:
    result = compare(si(), bl(consignee="UAB NOVAKOPA"))
    assert result.status == "MISMATCH"
    assert result.has_defect is True
    assert result.defect_fields == ["consignee"]


def test_several_differing_fields_are_reported_in_the_canonical_order() -> None:
    result = compare(
        si(),
        bl(gross_weight_kg="23,000 KG", shipper="ASIA PACIFIC PAPERBOARD TRADING PTE LTD"),
    )
    assert result.defect_fields == ["shipper", "gross_weight_kg"]


def test_labels_differing_while_values_agree_is_not_a_defect() -> None:
    """The whole trap: 'Load Port' and 'Port of Loading' hold the same value."""
    left = doc(DocumentType.SHIPPING_INSTRUCTION, **BASE)
    right = doc(
        DocumentType.BILL_OF_LADING,
        **{**BASE, "port_of_loading": "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)"},
    )
    assert compare(left, right).status == "OK"


def test_formatting_differences_are_not_defects() -> None:
    result = compare(
        si(),
        bl(gross_weight_kg="21577", container_count="1 X 40'HC", shipper="April Far East (M) Sdn Bhd"),
    )
    assert result.status == "OK"
    assert result.summary == "No mismatch detected"


def test_the_comparison_reports_what_it_compared() -> None:
    result = compare(si(), bl(consignee="UAB NOVAKOPA"))
    assert result.compared["consignee"] == ("MOORIM SP CO., LTD", "UAB NOVAKOPA")
    assert len(result.compared) == 7
