"""End to end over the provided bundle, through the provided loader."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/reference/sdoc-hackathon-bundle"


@pytest.fixture(scope="module")
def submission(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, object]]:
    out = tmp_path_factory.mktemp("run") / "submission.json"
    completed = subprocess.run(
        [sys.executable, "-m", "dock.cli", "--data", str(BUNDLE), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    parsed: dict[str, dict[str, object]] = json.loads(out.read_text())
    return parsed


def test_the_provided_loader_is_what_reads_the_inbox() -> None:
    """The bundle ships loader.py as the access path to the dataset; use it, do not
    reimplement it."""
    from dock.sources import bundle_inbox

    inbox = bundle_inbox(BUNDLE)
    assert type(inbox).__module__.endswith("loader")
    assert type(inbox).__name__ == "Inbox"
    assert len(inbox.emails()) == 520


def test_every_email_in_the_inbox_has_an_entry(
    submission: dict[str, dict[str, object]],
) -> None:
    expected = {p.stem for p in (BUNDLE / "inbox").glob("email_*.json")}
    assert set(submission) == expected


def test_the_shape_matches_the_sample_submission(
    submission: dict[str, dict[str, object]],
) -> None:
    sample = json.loads((BUNDLE / "sample_submission.json").read_text())
    reference = set(next(iter(sample.values())))
    for entry in submission.values():
        assert set(entry) == reference


def test_every_value_is_in_range(submission: dict[str, dict[str, object]]) -> None:
    from dock.classify import CATEGORIES
    from dock.review import REVIEW_REASONS

    for email_id, entry in submission.items():
        assert entry["category"] in CATEGORIES, email_id
        assert entry["status"] in ("OK", "MISMATCH", "NEEDS_REVIEW"), email_id
        assert isinstance(entry["has_defect"], bool), email_id
        assert isinstance(entry["defect_fields"], list), email_id
        assert entry["review_reason"] in (None, *REVIEW_REASONS), email_id


def test_defects_are_only_reported_where_a_defect_is_claimed(
    submission: dict[str, dict[str, object]],
) -> None:
    for email_id, entry in submission.items():
        assert bool(entry["defect_fields"]) == entry["has_defect"], email_id
        if entry["status"] != "MISMATCH":
            assert not entry["has_defect"], email_id


def test_review_reasons_appear_only_on_escalations(
    submission: dict[str, dict[str, object]],
) -> None:
    for email_id, entry in submission.items():
        if entry["status"] == "NEEDS_REVIEW":
            assert entry["review_reason"] is not None, email_id
        else:
            assert entry["review_reason"] is None, email_id


def test_non_comparison_emails_carry_a_neutral_verdict(
    submission: dict[str, dict[str, object]],
) -> None:
    for email_id, entry in submission.items():
        if entry["category"] != "BL_COMPARISON":
            assert entry["status"] == "OK", email_id
            assert entry["defect_fields"] == [], email_id


def test_the_pipeline_both_escalates_and_decides(
    submission: dict[str, dict[str, object]],
) -> None:
    """A system that never escalates is unreliable; one that always escalates is useless.

    The escalation count is the load-bearing number here, and it is 20 whether or not
    the 91 'please send the draft BL' emails are read as comparisons: they are, now,
    but they raise no document to chase, so they resolve rather than escalate. Letting
    them escalate scores identically on the weighted metric and drops escalation
    precision from 1.000 to 0.180 - which is the whole reason this assertion is
    pinned at 20 and not at "however many the classifier happened to route here".
    """
    statuses = [e["status"] for e in submission.values() if e["category"] == "BL_COMPARISON"]
    assert statuses.count("NEEDS_REVIEW") == 20
    assert statuses.count("OK") + statuses.count("MISMATCH") == 200
