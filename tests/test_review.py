"""Escalation.

NEEDS_REVIEW is scored as its own reliability axis, so it has to be a real decision with
a stated cause - never a shrug for anything the pipeline found hard. These tests pin both
halves: every escalation carries one of the four permitted reasons, and a case the
pipeline *can* decide never escalates.
"""

from pathlib import Path

import pytest

from dock.documents import Unreadable
from dock.extract import Document, DocumentType
from dock.pipeline import Attachment, adjudicate
from dock.review import REVIEW_REASONS

BUNDLE = Path(__file__).resolve().parents[1] / "docs/reference/sdoc-hackathon-bundle"

FIELDS = {
    "shipper": "APRIL FAR EAST (M) SDN BHD",
    "consignee": "MOORIM SP CO., LTD",
    "notify_party": "UAB NOVAKOPA",
    "port_of_loading": "PORT KLANG (WESTPORT), MALAYSIA",
    "port_of_discharge": "CALLAO, PERU",
    "container_count": "1 x 40'HC",
    "gross_weight_kg": "21,577 KG",
}


def readable(path: str, kind: DocumentType, **overrides: str) -> Attachment:
    values = {**FIELDS, **overrides}
    blanks = {k for k, v in overrides.items() if v == ""}
    return Attachment(
        path=path,
        document=Document(
            doc_type=kind,
            values={k: v for k, v in values.items() if v},
            blank_fields=blanks,
        ),
        error=None,
    )


def broken(path: str) -> Attachment:
    return Attachment(path=path, document=None, error=Unreadable(f"{path}: no text layer"))


SI = readable("attachments/e_SI.txt", DocumentType.SHIPPING_INSTRUCTION)
BL = readable("attachments/e_BL.txt", DocumentType.BILL_OF_LADING)


def test_the_four_permitted_reasons_and_no_others() -> None:
    assert REVIEW_REASONS == (
        "wrong_doc_type",
        "missing_attachment",
        "unreadable",
        "missing_value",
    )


def test_no_attachments_at_all() -> None:
    outcome = adjudicate([])
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.review_reason == "missing_attachment"
    assert outcome.has_defect is False
    assert outcome.defect_fields == []


def test_only_the_si_arrived() -> None:
    outcome = adjudicate([SI])
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.review_reason == "missing_attachment"


def test_only_the_bl_arrived() -> None:
    outcome = adjudicate([BL])
    assert outcome.review_reason == "missing_attachment"


def test_the_second_document_is_a_packing_list() -> None:
    other = readable("attachments/e_BL.txt", DocumentType.OTHER)
    outcome = adjudicate([SI, other])
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.review_reason == "wrong_doc_type"


def test_two_shipping_instructions_and_no_bl() -> None:
    outcome = adjudicate([SI, readable("attachments/e2_SI.txt", DocumentType.SHIPPING_INSTRUCTION)])
    assert outcome.review_reason == "wrong_doc_type"


def test_a_file_that_will_not_open() -> None:
    outcome = adjudicate([SI, broken("attachments/e_BL.pdf")])
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.review_reason == "unreadable"


def test_both_files_unreadable() -> None:
    outcome = adjudicate([broken("attachments/e_SI.pdf"), broken("attachments/e_BL.pdf")])
    assert outcome.review_reason == "unreadable"


def test_a_field_left_blank_by_the_customer() -> None:
    outcome = adjudicate(
        [
            readable("attachments/e_SI.txt", DocumentType.SHIPPING_INSTRUCTION, gross_weight_kg=""),
            BL,
        ]
    )
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.review_reason == "missing_value"
    assert outcome.has_defect is False


def test_a_blank_field_is_never_reported_as_a_mismatch() -> None:
    outcome = adjudicate(
        [readable("attachments/e_SI.txt", DocumentType.SHIPPING_INSTRUCTION, consignee=""), BL]
    )
    assert outcome.defect_fields == []


def test_unreadable_outranks_missing_value() -> None:
    """The unreadable file could hold anything; reporting a blank field first would
    understate the problem."""
    outcome = adjudicate(
        [
            readable("attachments/e_SI.txt", DocumentType.SHIPPING_INSTRUCTION, consignee=""),
            broken("attachments/e_BL.pdf"),
        ]
    )
    assert outcome.review_reason == "unreadable"


def test_a_decidable_pair_does_not_escalate() -> None:
    assert adjudicate([SI, BL]).status == "OK"
    assert adjudicate([SI, BL]).review_reason is None


def test_a_real_defect_is_reported_as_a_mismatch_not_escalated() -> None:
    outcome = adjudicate(
        [
            SI,
            readable(
                "attachments/e_BL.txt", DocumentType.BILL_OF_LADING, consignee="CLIFFORD PAPER INC"
            ),
        ]
    )
    assert outcome.status == "MISMATCH"
    assert outcome.defect_fields == ["consignee"]
    assert outcome.review_reason is None


class TestAgainstTheRealCorpus:
    """The corpus carries one designed example of each escalation cause."""

    @pytest.mark.parametrize(
        ("email_id", "reason"),
        [
            ("email_501", "wrong_doc_type"),
            ("email_502", "wrong_doc_type"),
            ("email_506", "missing_attachment"),
            ("email_507", "missing_attachment"),
            ("email_511", "unreadable"),
            ("email_512", "unreadable"),
            ("email_516", "missing_value"),
            ("email_520", "missing_value"),
        ],
    )
    def test_reason(self, email_id: str, reason: str) -> None:
        from dock.pipeline import process
        from dock.sources import bundle_inbox

        inbox = bundle_inbox(BUNDLE)
        result = process(inbox, inbox.get(email_id))
        assert result["category"] == "BL_COMPARISON"
        assert result["status"] == "NEEDS_REVIEW"
        assert result["review_reason"] == reason
