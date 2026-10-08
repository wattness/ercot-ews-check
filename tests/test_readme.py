import re
import subprocess
import sys

from ercot_ews_check.cli import main

from helpers import ROOT

README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_measured_block_matches_the_script():
    block = re.search(r"<!-- measure:start -->\n```\n(.*?)```\n<!-- measure:end -->", README, re.S)
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "measure.py")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert block.group(1) == out


def test_python_example_runs(monkeypatch):
    code = re.search(r"```python\n(.*?)```", README, re.S).group(1)
    monkeypatch.chdir(ROOT)
    exec(compile(code, "README.md", "exec"), {"print": lambda *a, **k: None})


def test_first_lines_say_unofficial():
    head = README.splitlines()[:4]
    assert any("Not affiliated with or endorsed by ERCOT" in line for line in head)


def test_quickstart_output_is_real(capsys, monkeypatch):
    block = re.search(r"```\n(examples/broken/as-only-offer\.xml: .*?)```", README, re.S).group(1)
    monkeypatch.chdir(ROOT)
    main(["check", "examples/broken/as-only-offer.xml"])
    out = capsys.readouterr().out.splitlines()
    shown = [line for line in block.splitlines() if line.strip() != "..."]
    assert shown and all(line in out for line in shown)
