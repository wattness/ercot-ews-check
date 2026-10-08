#!/usr/bin/env python3
"""Write the terminal image in docs/img/, in a light and a dark variant, from the CLI's output.

    python scripts/render_terminal.py

The image shows a prompt with the command, then exactly what the command prints, in rows of at
most COLUMNS characters, broken after the last space that fits, as `fold -s` breaks them.
tests/test_render_terminal.py fails when an image no longer shows what its command prints.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ARGS = ["check", "examples/broken/as-only-offer.xml"]
NAME = "check-broken-as-only-offer"
COLUMNS = 88
FONT, LINE, BASELINE, PAD = 14, 20, 15, 16  # px; BASELINE is measured from the top of a row
# An SVG shown as an image uses the viewer's fonts, whose widths differ (SF Mono is wider than
# 0.6 em, Consolas narrower). Each run of text is placed at its column and held to 0.6 em per
# character with textLength, so rows keep to one grid and fit the frame. Runs are sibling
# <tspan>s: WebKit misplaces text when textLength is set on an element that holds a <tspan>.
CELL = 0.6 * FONT
FAMILY = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'
# GitHub's Primer colour tokens: bgColor-muted and fgColor-default (a README code block's
# background and text), borderColor-default, fgColor-muted (the prompt), fgColor-danger ([error]).
THEMES = {
    "light": ("#f6f8fa", "#d1d9e0", "#1f2328", "#59636e", "#d1242f"),
    "dark": ("#151b23", "#3d444d", "#f0f6fc", "#9198a1", "#f85149"),
}


def capture(args: list[str]) -> list[str]:
    """The lines ``ercot-ews-check ARGS`` prints, run from the repository root on this checkout."""
    proc = subprocess.run(
        [sys.executable, "-m", "ercot_ews_check", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
    )
    if proc.returncode > 1 or proc.stderr:
        sys.exit(f"ercot-ews-check exited {proc.returncode}:\n{proc.stderr}")
    return proc.stdout.splitlines()


def rows(runs: list[tuple[str, str]]) -> list[list[tuple[int, str, str]]]:
    """Cut a line's (text, class) runs into rows of at most COLUMNS characters, as
    (column, text, class), breaking after the last space that fits, as `fold -s` does."""
    line = "".join(text for text, _ in runs)
    cuts, start = [], 0
    while len(line) - start > COLUMNS:
        space = line.rfind(" ", start, start + COLUMNS)
        start = space + 1 if space > start else start + COLUMNS
        cuts.append(start)
    out, col, pos = [[]], 0, 0
    for text, cls in runs:
        while text:
            if cuts and pos == cuts[0]:
                cuts.pop(0)
                out.append([])
                col = 0
            take = min(len(text), (cuts[0] if cuts else len(line)) - pos)
            part, text = text[:take], text[take:]
            out[-1].append((col, part, cls))
            col += take
            pos += take
    return out


def svg(command: str, output: list[str], theme: str) -> str:
    """One <text> per line; within it, one <tspan> per run of a row."""
    bg, border, fg, prompt, error = THEMES[theme]
    lines = [[("$", "prompt"), (f" {command}", "")]] + [
        [(part, "error" if part == "[error]" else "") for part in re.split(r"(\[error\])", line)]
        for line in output
    ]
    texts, top = [], PAD
    for runs in lines:
        spans = []
        for row in rows(runs):
            for col, text, cls in row:
                attrs = f'x="{PAD + col * CELL:g}" y="{top + BASELINE}"'
                attrs += f' textLength="{len(text) * CELL:g}"' + (f' class="{cls}"' if cls else "")
                spans.append(f"<tspan {attrs}>{escape(text)}</tspan>")
            top += LINE
        texts.append(f'<text xml:space="preserve">{"".join(spans)}</text>')
    w, h, body = 2 * PAD + round(COLUMNS * CELL), top + PAD, "\n".join(texts)
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>{escape(command)}</title>
<style>
text {{ font-family: {FAMILY}; font-size: {FONT}px; fill: {fg}; }}
.prompt {{ fill: {prompt}; }}
.error {{ fill: {error}; }}
</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="6" fill="{bg}" stroke="{border}"/>
{body}
</svg>
"""


def main() -> int:
    command, output = f"ercot-ews-check {shlex.join(ARGS)}", capture(ARGS)
    for theme in THEMES:
        path = ROOT / "docs" / "img" / f"{NAME}-{theme}.svg"
        path.parent.mkdir(exist_ok=True)
        path.write_text(svg(command, output, theme), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
