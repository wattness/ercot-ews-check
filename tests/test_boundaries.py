import subprocess
import sys

from helpers import ROOT

SCRIPT = ROOT / "scripts" / "check_boundaries.py"


def run(*paths):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, paths)], capture_output=True, text=True
    )


def test_repository_passes():
    result = run()
    assert result.returncode == 0, result.stdout


def test_undeclared_import_fails(tmp_path):
    bad = tmp_path / "probe.py"
    bad.write_text("import somewhere_private.module\n", encoding="utf-8")
    result = run(bad)
    assert result.returncode == 1 and "somewhere_private" in result.stdout
