import json
import subprocess
import sys
from pathlib import Path

import pytest

from ercot_ews_check.cli import main

from helpers import ROOT

GOOD = str(ROOT / "examples" / "energy-only-offer.xml")
BAD = str(ROOT / "examples" / "broken" / "as-only-offer.xml")


def run(capsys, *args):
    code = main(list(args))
    return code, capsys.readouterr().out


def test_check(capsys):
    assert run(capsys, "check", GOOD)[0] == 0
    code, out = run(capsys, "check", BAD)
    assert code == 1 and "BLOCKED" in out and "see: D001" in out


def test_check_json(capsys):
    code, out = run(capsys, "check", "--json", BAD)
    data = json.loads(out)
    assert code == 1 and data["blocked"] and data["schema"] == "invalid"


def test_strict_fails_on_warnings(capsys, tmp_path):
    doc = tmp_path / "w.xml"
    text = Path(GOOD).read_text(encoding="utf-8")
    doc.write_text(
        text.replace("<xvalue>5.0</xvalue>", "<xvalue>5.05</xvalue>", 1), encoding="utf-8"
    )
    assert run(capsys, "check", str(doc))[0] == 0
    assert run(capsys, "check", "--strict", str(doc))[0] == 1


def test_lookup_show_reproduce(capsys):
    code, out = run(capsys, "lookup", "TimeStamp")
    assert code == 0 and out.startswith("D021")
    assert run(capsys, "lookup", "no-such-term")[0] == 1
    code, out = run(capsys, "show", "D021")
    assert code == 0 and "Notification.xsd:46" in out
    code, out = run(capsys, "reproduce", "D021")
    assert code == 0 and "--- invalid ---" in out and "--- valid ---" in out
    assert run(capsys, "show", "D999")[0] == 1


def test_show_json(capsys):
    data = json.loads(run(capsys, "show", "--json", "D033")[1])
    assert data["protocols_say"]["section"].startswith("Nodal Protocols 3.9.1")


def test_explain(capsys):
    code, out = run(capsys, "explain", BAD)
    assert code == 1 and out.splitlines()[1].startswith("BLOCKED")
    assert "Possibly related catalogue entry D001" in out
    assert run(capsys, "explain", GOOD)[0] == 0


def test_unreadable_file_is_not_a_verdict(capsys, tmp_path):
    code = main(["check", str(tmp_path / "missing.xml"), GOOD])
    captured = capsys.readouterr()
    assert code == 2 and "cannot read" in captured.err and "OK" in captured.out
    assert main(["explain", str(tmp_path)]) == 2


def test_show_renders_observations_without_quotation_marks(capsys):
    out = run(capsys, "show", "D005")[1]
    assert "ERCOT says" not in out and "Observed: expirationTime is the only solid" in out


def test_verify(capsys):
    code, out = run(capsys, "verify")
    assert code == 0 and "still present in vendored sources" in out


def test_verify_live_without_network_fails_cleanly(capsys):
    code = main(["verify", "--live"])
    captured = capsys.readouterr()
    assert code == 2 and captured.err.startswith("ercot-ews-check: ")
    assert "Traceback" not in captured.err


@pytest.mark.network
def test_verify_live(capsys):
    code, out = run(capsys, "verify", "--live")
    assert code in (0, 1) and "present in live sources" in out


def test_closed_pipe_is_quiet():
    proc = subprocess.Popen(
        [sys.executable, "-m", "ercot_ews_check", "rules"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.stdout.readline()
    proc.stdout.close()
    err = proc.stderr.read().decode()
    proc.wait()
    assert "Traceback" not in err


def test_rules_and_sources(capsys):
    code, out = run(capsys, "rules", "--owner", "ReplayDetectionType")
    assert code == 0 and "Message.xsd:" in out
    code, out = run(capsys, "sources")
    assert code == 0 and "match MANIFEST.json" in out


def test_examples(capsys):
    code, out = run(capsys, "examples")
    assert code == 0 and "ASOnlyOffer-Example.xml: invalid" in out


def test_mutate_json(capsys):
    data = json.loads(run(capsys, "mutate", "--json", GOOD)[1])
    assert data["rule"]["survived"] == [] and data["schema"]["survived"] == []


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
