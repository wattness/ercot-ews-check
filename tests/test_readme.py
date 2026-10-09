import re
import subprocess
import sys

from ercot_ews_check import schema
from ercot_ews_check.checker import check_file

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
    head = README.splitlines()[:5]
    assert any("Not affiliated with or endorsed by ERCOT" in line for line in head)


def test_limits_stated_in_the_readme_are_the_codes():
    assert f"more than {schema.MAX_DEPTH} levels" in README
    assert f"first {schema.MAX_ERRORS} schema errors" in README


def test_image_description_matches_the_report():
    pattern = r'alt="Terminal: ercot-ews-check check (\S+) reports (\w+), schema (\w+), (\d+) '
    file, verdict, state, count = re.search(pattern, README).groups()
    rep = check_file(ROOT / file)
    shown = (verdict, state, int(count))
    assert shown == ("BLOCKED" if rep.blocked else "OK", rep.schema, len(rep.findings))


def test_links_the_notifications_page():
    assert "(docs/notifications.md)" in README
