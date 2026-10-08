#!/usr/bin/env python3
"""Fail if any Python file imports something other than the standard library,
this package, or a declared dependency.

    python scripts/check_boundaries.py [paths...]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"ercot_ews_check", "xmlschema", "yaml", "pytest", "helpers", "conftest"}
SKIP = {
    "vendor",
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def _rel(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def files(paths: list[Path]) -> list[Path]:
    out = []
    for base in paths:
        for p in [base] if base.is_file() else base.rglob("*.py"):
            if p.is_file() and not SKIP & set(_rel(p).parts):
                out.append(p)
    return sorted(out)


def bad_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            top = name.split(".")[0]
            if top not in sys.stdlib_module_names and top not in ALLOWED:
                found.append(f"{_rel(path)}:{node.lineno}: imports {name}")
    return found


def main(argv: list[str]) -> int:
    paths = [Path(a).resolve() for a in argv] or [ROOT]
    problems = [line for p in files(paths) for line in bad_imports(p)]
    print("\n".join(problems) if problems else "imports ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
