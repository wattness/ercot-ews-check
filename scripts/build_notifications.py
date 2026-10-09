#!/usr/bin/env python3
"""Write the generated block of docs/notifications.md from the vendored portal and schemas.

python scripts/build_notifications.py           # write
python scripts/build_notifications.py --check   # exit 1 if the block is out of date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ercot_ews_check.notifications import update  # noqa: E402

TARGET = ROOT / "docs" / "notifications.md"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    text = TARGET.read_text(encoding="utf-8")
    fresh = update(text)
    if args.check:
        if fresh != text:
            print(f"{TARGET.relative_to(ROOT)} is out of date; run scripts/build_notifications.py")
            return 1
        return 0
    TARGET.write_text(fresh, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
