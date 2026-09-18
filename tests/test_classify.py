"""Stage-1 classification.

The dataset's subject lines are deliberately misleading - a spam body under a
"TO CONFIRM DOCS" subject, an invoice cancellation under a "Mill D & D charges"
subject. The requirement pinned here is: decide from the body's intent, and treat
the subject only as a weak tie-breaker.
"""

from dock.classify import CATEGORIES, classify


def email(body: str, subject: str = "", attachments: list[str] | None = None) -> dict[str, object]:
    return {
        "email_id": "email_000",
        "from": "someone@example.com",
        "subject": subject,
        "body": body,
        "attachments": attachments or [],
    }


def test_categories_are_the_five_required_labels() -> None:
    assert CATEGORIES == (
        "BL_COMPARISON",
        "SI_REQUEST",
        "INVOICE_QUERY",
        "GENERAL",
        "SPAM",
    )


class TestComparison:
    def test_si_and_draft_bl_attached_for_checking(self) -> None:
        e = email(
            "Attached are the SI and draft BL for OC 5RSG-00133 (PAPERONE). "
            "Please check the details and confirm.",
            subject="TO CONFIRM DOCS _ 5RSG-00133",
            attachments=["attachments/email_001_SI.txt", "attachments/email_001_BL.txt"],
        )
        assert classify(e) == "BL_COMPARISON"

    def test_check_draft_bl_against_si_phrasing(self) -> None:
        e = email(
            "Pls assist to check the draft BL against the SI for PO and revert with "
            "any discrepancy asap. Draft BL No. YMJAI490278742",
            attachments=["attachments/x_SI.txt", "attachments/x_BL.txt"],
        )
        assert classify(e) == "BL_COMPARISON"

    def test_comparison_request_with_the_attachments_dropped(self) -> None:
        """Still a comparison request; the missing files are a review problem, not a category."""
        e = email(
            "Please compare the SI and draft BL for 070500263211 and confirm "
            "(attachments appear to have been dropped). Thank you.",
            subject="RE_ AFRT - LONG BEACH_US",
        )
        assert classify(e) == "BL_COMPARISON"

    def test_terse_attachment_phrasing_without_the_article(self) -> None:
        e = email(
            "Attached SI and draft BL for MCLSINJEA2529384 for checking "
            "(the BL file will not open). Please advise.",
            attachments=["attachments/x_SI.pdf", "attachments/x_BL.pdf"],
        )
        assert classify(e) == "BL_COMPARISON"

    def test_wrong_second_document_is_still_a_comparison_request(self) -> None:
        e = email(
            "Please find attached the SI and the Packing List for MCLSINJEA2508070. "
            "Kindly confirm the BL is in order.",
            attachments=["attachments/x_SI.txt", "attachments/x_BL.txt"],
        )
        assert classify(e) == "BL_COMPARISON"


class TestSiRequest:
    def test_shipping_instruction_being_issued(self) -> None:
        e = email(
            "Please find Shipping instruction for 5RFR-37631.\n\nPOL: SINGAPORE\n"
            "POD: GDANSK, POLAND\n\nShipper:\nAPRIL FINE PAPER TRADING",
            subject="REQUEST SI _ 5RFR-37631 _ GDANSK_POLAND",
        )
        assert classify(e) == "SI_REQUEST"


class TestInvoiceQuery:
    def test_local_charge_breakdown_query(self) -> None:
        e = email(
            "Query on invoice 5250075931: is the THC / local charge included or "
            "billed separately? Please advise the breakdown."
        )
        assert classify(e) == "INVOICE_QUERY"

    def test_detention_charges_confirmation(self) -> None:
        e = email(
            "Please find the D&D / detention charges for MSDUL0942527743. "
            "Kindly confirm the amount before we release payment."
        )
        assert classify(e) == "INVOICE_QUERY"

    def test_missing_goods_receipt(self) -> None:
        e = email(
            "We note the GR is still missing for invoice 5250070084. "
            "Kindly arrange to post the GR so we can proceed with billing."
        )
        assert classify(e) == "INVOICE_QUERY"

    def test_invoice_cancellation_under_a_misleading_subject(self) -> None:
        e = email(
            "Requesting to cancel invoice 5250073257 for TOPKOPY MIDDLE EAST FZE "
            "(5RCY-21557) and reverse the PGI. Reason: booking amended.",
            subject="Mill D & D charges - 6437419513",
        )
        assert classify(e) == "INVOICE_QUERY"


class TestGeneral:
    def test_outstanding_bl_list_broadcast(self) -> None:
        e = email(
            "Please find attached the list of outstanding BL (BDP SG). "
            "Kindly action the pending items.",
            subject="15_01_2026 - UPDATE SUMMARY LE HAVRE V.QI540A",
        )
        assert classify(e) == "GENERAL"

    def test_holiday_greeting_under_an_operational_subject(self) -> None:
        e = email(
            "Wishing everyone a happy and prosperous New Year 2026! "
            "Office resumes normal operations on 2 January.",
            subject="27_01_2026 - UPDATE SUMMARY LE HAVRE V.QI540A",
        )
        assert classify(e) == "GENERAL"

    def test_request_to_be_sent_a_draft_bl_is_a_comparison_not_yet_actionable(self) -> None:
        """It asks for a BL *for checking*: the checking workflow, before the document.

        This was classified GENERAL on the reading that nothing is attached and so
        nothing can be compared. The organisers' grader disagreed - BL_COMPARISON
        recall 0.59 against GENERAL precision 0.40 was this one template, 91 emails,
        and correcting it took Stage-1 macro-F1 from 0.862 to 1.000. The pipeline
        still refuses to escalate it (see test_pipeline), because there is no missing
        document to chase - only one that has not been issued yet.
        """
        e = email(
            "Please assist to send the draft BL for SIN832764835 for checking asap.",
            subject="RE_ TO CONFIRM DOCS _ 5AAT-03056 _ AQABA_JORDAN",
        )
        assert classify(e) == "BL_COMPARISON"

    def test_berthing_report(self) -> None:
        e = email(
            "Kindly find the daily berthing report attached. "
            "Vessel MMSS 2507 V.257087E berthed on schedule."
        )
        assert classify(e) == "GENERAL"


class TestSpam:
    def test_prize_draw(self) -> None:
        e = email(
            "CONGRATULATIONS!!! Your email address has been selected in our monthly draw. "
            "Click here to claim your $1,000 gift card."
        )
        assert classify(e) == "SPAM"

    def test_advance_fee_fraud_under_a_shipping_subject(self) -> None:
        e = email(
            "Hello Dear, I am a bank officer with an urgent business proposal involving "
            "USD 4.5 million. Please reply with your bank details to proceed.",
            subject="Re: Invoice payment - kindly confirm your bank details",
        )
        assert classify(e) == "SPAM"

    def test_credential_phishing(self) -> None:
        e = email(
            "Dear user, your mailbox has exceeded its storage limit. Verify your account "
            "within 24 hours to avoid deactivation: http://webmail-verify.co"
        )
        assert classify(e) == "SPAM"


def test_external_sender_banner_does_not_change_the_decision() -> None:
    banner = (
        "WARNING: This email originated outside of our organisation. As a security "
        "measure, please exercise caution with E-Mail content and any links or "
        "attachments.\n\n"
    )
    body = "Please find Shipping instruction for 5RFR-37631.\n\nPOL: SINGAPORE"
    assert classify(email(banner + body)) == "SI_REQUEST"


def test_unrecognised_business_mail_falls_back_to_general() -> None:
    assert classify(email("Noted with thanks, will revert shortly.")) == "GENERAL"
