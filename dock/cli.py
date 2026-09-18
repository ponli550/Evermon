"""``python -m dock.cli --data <bundle> --out submission.json``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from dock.pipeline import explain_entry, process
from dock.sources import bundle_inbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dock",
        description="Triage a shipping-document inbox and report SI/BL discrepancies.",
    )
    parser.add_argument(
        "--data",
        default="docs/reference/sdoc-hackathon-bundle",
        help="Dataset directory (containing inbox/ and attachments/), or a server URL.",
    )
    parser.add_argument("--out", default="submission.json", help="Where to write the submission.")
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print the decision for every email as it is made.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inbox = bundle_inbox(args.data)

    submission: dict[str, dict[str, object]] = {}
    for email in inbox.emails():
        email_id = email["email_id"]
        entry = process(inbox, email)
        submission[email_id] = entry
        if args.explain:
            print(f"{email_id}  {explain_entry(entry)}")

    out = Path(args.out)
    if out.parent != Path():
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(submission, indent=2) + "\n")

    categories = Counter(e["category"] for e in submission.values())
    comparisons = [e for e in submission.values() if e["category"] == "BL_COMPARISON"]
    statuses = Counter(e["status"] for e in comparisons)
    print(f"{len(submission)} emails -> {out}", file=sys.stderr)
    print(
        "  " + "  ".join(f"{name}={count}" for name, count in sorted(categories.items())),
        file=sys.stderr,
    )
    print(
        "  comparisons: "
        + "  ".join(f"{name}={count}" for name, count in sorted(statuses.items())),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
