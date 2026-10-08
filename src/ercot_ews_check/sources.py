"""Paths to the vendored ERCOT files and the discrepancy catalogue.

Installed from a wheel, both live under ``ercot_ews_check/_data``. In a source
checkout they are the repository's ``vendor/`` and ``discrepancies/`` folders.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent
_CHECKOUT = _PACKAGE.parents[1]


def _root(name: str) -> Path:
    packaged = _PACKAGE / "_data" / name
    return packaged if packaged.is_dir() else _CHECKOUT / name


def vendor_dir() -> Path:
    return _root("vendor")


def discrepancies_dir() -> Path:
    return _root("discrepancies")


def xsd_dir() -> Path:
    return vendor_dir() / "ercot" / "api-specs" / "ews" / "xsds"


def api_specs_examples_dir() -> Path:
    return vendor_dir() / "ercot" / "api-specs" / "ews" / "examples"


def portal_dir() -> Path:
    return vendor_dir() / "ercot" / "developer.ercot.com"


def portal_index_path() -> Path:
    return portal_dir() / "search" / "search_index.json"


@lru_cache(maxsize=1)
def manifest() -> dict:
    return json.loads((vendor_dir() / "MANIFEST.json").read_text(encoding="utf-8"))


def api_specs_commit() -> str:
    return manifest()["api_specs_commit"]


@lru_cache(maxsize=1)
def portal_docs() -> tuple[dict, ...]:
    """The developer portal's search index: one dict per page or anchor."""
    return tuple(json.loads(portal_index_path().read_text(encoding="utf-8"))["docs"])


def portal_url(location: str) -> str:
    return f"https://developer.ercot.com/{location}"


def live_url(path: str) -> str:
    """Where today's copy of a vendored file is: api-specs main, or the page itself."""
    entry = next(e for e in manifest()["files"] if e["path"] == path)
    commit = entry.get("commit")
    return entry["url"].replace(f"/{commit}/", "/main/") if commit else entry["url"]


def verify() -> list[str]:
    """Vendored files that are missing or differ from MANIFEST.json."""
    bad = []
    for entry in manifest()["files"]:
        path = vendor_dir() / entry["path"]
        if not path.is_file():
            bad.append(f"missing: {entry['path']}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            bad.append(f"modified: {entry['path']}")
    return bad
