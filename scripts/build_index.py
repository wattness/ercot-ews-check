#!/usr/bin/env python3
"""Write docs/discrepancies.md from discrepancies/*.yaml.

python scripts/build_index.py           # write
python scripts/build_index.py --check   # exit 1 if the file is out of date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ercot_ews_check.discrepancies import render_index  # noqa: E402

TARGET = ROOT / "docs" / "discrepancies.md"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    text = render_index()
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != text:
            print(f"{TARGET.relative_to(ROOT)} is out of date; run scripts/build_index.py")
            return 1
        return 0
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
