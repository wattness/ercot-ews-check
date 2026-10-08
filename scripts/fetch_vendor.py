#!/usr/bin/env python3
"""Verify or refresh the ERCOT files in vendor/.

    python scripts/fetch_vendor.py verify          # offline: hashes against MANIFEST.json
    python scripts/fetch_vendor.py refresh         # download from the pinned sources, compare
    python scripts/fetch_vendor.py refresh --write # ...and overwrite local copies that differ
    python scripts/fetch_vendor.py update --commit <sha>   # move the api-specs pin (maintainers)

Vendored files are never edited by hand. A file that differs from its source
is replaced by a fresh download, and MANIFEST.json records the new hash.
Exit status: 0 when every file matches (or was rewritten), 1 when a file
differs, is missing or could not be downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor"
MANIFEST = VENDOR / "MANIFEST.json"
API_SPECS_RAW = "https://raw.githubusercontent.com/ercot/api-specs/{commit}/{path}"
API_SPECS_TREE = "https://api.github.com/repos/ercot/api-specs/git/trees/{commit}?recursive=1"
USER_AGENT = "Mozilla/5.0 (compatible; vendor-refresh)"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get(url: str, timeout: float = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.build_opener().open(req, timeout=timeout) as resp:
        return resp.read()


def terms_text(page: bytes) -> bytes:
    """The agreement and the copyright line from ercot.com/help/terms, as plain text."""
    s = page.decode("utf-8")
    start = s.index("Last updated:")
    start = s.rindex("<p", 0, start)
    end = s.index("</div>", s.index("10. ERCOT reserves"))
    paras = re.findall(r"<p[^>]*>(.*?)</p>", s[start:end], re.S)
    lines = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in paras]
    title = html.unescape(re.search(r"<title>\s*(.*?)\s*</title>", s, re.S).group(1))
    footer = re.search(r'class="[^"]*copyright[^"]*">(.*?)<', s, re.S)
    out = [title.split("|")[0].strip(), ""]
    for line in lines:
        out += [line, ""]
    if footer:
        out.append(html.unescape(footer.group(1)).strip())
    return ("\n".join(out).rstrip() + "\n").encode("utf-8")


def fetch(entry: dict) -> bytes:
    body = get(entry["url"])
    if entry.get("extract") == "terms-text":
        body = terms_text(body)
    return body


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def cmd_verify(_args) -> int:
    bad = 0
    for e in load()["files"]:
        path = VENDOR / e["path"]
        if not path.is_file():
            print(f"missing   {e['path']}")
            bad += 1
        elif sha256(path.read_bytes()) != e["sha256"]:
            print(f"modified  {e['path']}")
            bad += 1
    n = len(load()["files"])
    print(f"{n - bad} of {n} vendored files match MANIFEST.json")
    return 1 if bad else 0


def cmd_refresh(args) -> int:
    manifest = load()
    changed = failed = 0
    for e in manifest["files"]:
        try:
            body = fetch(e)
        except (OSError, ValueError) as exc:  # URLError and HTTPError are OSErrors
            print(f"unreachable {e['path']}: {exc}")
            failed += 1
            continue
        if sha256(body) == e["sha256"]:
            continue
        changed += 1
        print(
            f"changed   {e['path']} (source now {sha256(body)[:12]}, manifest {e['sha256'][:12]})"
        )
        if args.write:
            (VENDOR / e["path"]).write_bytes(body)
            e.update(sha256=sha256(body), bytes=len(body), retrieved=date.today().isoformat())
    if args.write and changed:
        save(manifest)
    print(
        f"{len(manifest['files'])} files checked: {changed} changed upstream, {failed} unreachable"
    )
    return 1 if failed or (changed and not args.write) else 0


def cmd_update(args) -> int:
    """Re-vendor ews/ from api-specs at a new commit and record the pin."""
    manifest = load()
    tree = json.loads(get(API_SPECS_TREE.format(commit=args.commit)))
    commit = tree["sha"]
    wanted = sorted(
        t["path"] for t in tree["tree"] if t["type"] == "blob" and t["path"].startswith("ews/")
    )
    kept = [e for e in manifest["files"] if not e["path"].startswith("ercot/api-specs/")]
    today = date.today().isoformat()
    fresh = []
    for rel in wanted:
        url = API_SPECS_RAW.format(commit=commit, path=rel)
        body = get(url)
        out = VENDOR / "ercot" / "api-specs" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(body)
        fresh.append(
            {
                "path": f"ercot/api-specs/{rel}",
                "url": url,
                "commit": commit,
                "retrieved": today,
                "bytes": len(body),
                "sha256": sha256(body),
            }
        )
    manifest["api_specs_commit"] = commit
    manifest["files"] = fresh + kept
    save(manifest)
    print(f"api-specs pinned at {commit}: {len(fresh)} files")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    r = sub.add_parser("refresh")
    r.add_argument("--write", action="store_true", help="overwrite local copies that differ")
    r.set_defaults(func=cmd_refresh)
    u = sub.add_parser("update")
    u.add_argument("--commit", required=True, help="api-specs commit sha or branch")
    u.set_defaults(func=cmd_update)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
