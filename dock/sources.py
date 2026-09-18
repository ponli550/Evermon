"""Access to the dataset, through the loader the organisers shipped with it.

The bundle's own ``loader.py`` is the documented way in - it reads the static folder and
the docker HTTP server behind one interface. It is imported from the data directory at
run time and driven directly, rather than reimplemented here, so this pipeline reads the
dataset exactly the way the bundle says to.

If the loader is absent (someone points --data at a bare inbox/ + attachments/ tree) a
minimal stdlib equivalent stands in, and says so.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Protocol


class InboxLike(Protocol):
    def emails(self) -> list[dict[str, Any]]: ...

    def get(self, email_id: str) -> dict[str, Any]: ...

    def read_bytes(self, att_path: str) -> bytes: ...


def load_bundled_loader(data_dir: Path) -> Any | None:
    """Import the ``Inbox`` class from the bundle's own loader.py, if it is there."""
    loader_py = data_dir / "loader.py"
    if not loader_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("sdoc_loader", loader_py)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("sdoc_loader", module)
    spec.loader.exec_module(module)
    return getattr(module, "Inbox", None)


class _FallbackInbox:
    """Stdlib stand-in with the same surface, for a bundle that has no loader.py."""

    def __init__(self, source: str) -> None:
        self.source = Path(source)

    def emails(self) -> list[dict[str, Any]]:
        inbox_dir = self.source / "inbox"
        return [json.loads(p.read_text()) for p in sorted(inbox_dir.glob("email_*.json"))]

    def get(self, email_id: str) -> dict[str, Any]:
        record: dict[str, Any] = json.loads(
            (self.source / "inbox" / f"{email_id}.json").read_text()
        )
        return record

    def read_bytes(self, att_path: str) -> bytes:
        return (self.source / att_path).read_bytes()


def bundle_inbox(data_dir: str | Path) -> InboxLike:
    """Open the dataset at ``data_dir`` using the bundle's loader where available."""
    data_dir = Path(data_dir)
    inbox_cls = load_bundled_loader(data_dir)
    if inbox_cls is None:
        return _FallbackInbox(str(data_dir))
    inbox: InboxLike = inbox_cls(str(data_dir))
    return inbox
