import shlex
import xml.etree.ElementTree as ET

import pytest

from ercot_ews_check.cli import main

from helpers import ROOT

SVG = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_image_shows_what_its_command_prints(theme, capsys, monkeypatch):
    image = ROOT / "docs" / "img" / f"check-broken-as-only-offer-{theme}.svg"
    prompt, *shown = ["".join(t.itertext()) for t in ET.parse(image).iter(f"{SVG}text")]
    dollar, program, *args = shlex.split(prompt)
    assert (dollar, program) == ("$", "ercot-ews-check")
    monkeypatch.chdir(ROOT)
    main(args)
    assert shown == capsys.readouterr().out.splitlines(), "run python scripts/render_terminal.py"
