import re

from ercot_ews_check import sources


def test_vendored_files_match_the_manifest():
    assert sources.verify() == []


def test_every_vendored_file_is_listed():
    """Everything in vendor/ except our own NOTICE, MANIFEST.json and licence texts."""
    listed = {e["path"] for e in sources.manifest()["files"]}
    root = sources.vendor_dir()
    on_disk = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name not in ("NOTICE", "MANIFEST.json") and "licenses" not in p.parts
    }
    assert on_disk == listed


def test_api_specs_is_pinned():
    commit = sources.api_specs_commit()
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    for e in sources.manifest()["files"]:
        if e["path"].startswith("ercot/api-specs/"):
            assert e["commit"] == commit and commit in e["url"]


def test_manifest_entries_are_complete():
    for e in sources.manifest()["files"]:
        assert {"path", "url", "retrieved", "bytes", "sha256"} <= e.keys()
