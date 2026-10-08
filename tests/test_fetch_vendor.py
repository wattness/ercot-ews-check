import importlib.util

from helpers import ROOT

spec = importlib.util.spec_from_file_location("fetch_vendor", ROOT / "scripts" / "fetch_vendor.py")
fetch_vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_vendor)


def test_verify_offline(capsys):
    assert fetch_vendor.main(["verify"]) == 0
    assert "vendored files match MANIFEST.json" in capsys.readouterr().out


def test_terms_text_extraction():
    page = b"""<html><head><title>Terms of Use | ERCOT</title></head><body><div>
<p>Last updated: 07/20/2023</p><p>1. First &amp; foremost.</p>
<p>10. ERCOT reserves the right.</p></div>
<span class="footer-copyright">&copy; 1996-2026 ERCOT</span></body></html>"""
    text = fetch_vendor.terms_text(page).decode()
    assert text.splitlines()[0] == "Terms of Use"
    assert "1. First & foremost." in text and text.rstrip().endswith("1996-2026 ERCOT")


def test_refresh_fails_when_a_source_is_unreachable(capsys):
    assert fetch_vendor.main(["refresh"]) == 1
    assert "unreachable" in capsys.readouterr().out
