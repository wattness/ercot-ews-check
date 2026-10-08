import os
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig

import pytest
import yaml

from helpers import ROOT

SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
EXAMPLE = "examples/broken/as-only-offer.xml"
# Every command the skill gives, with the exit status it must have on the example.
EXPECTED = {
    "ercot-ews-check --version": 0,
    "ercot-ews-check explain path/to/document.xml": 1,
    "ercot-ews-check lookup plannedSart": 0,
    "ercot-ews-check show D020": 0,
    "ercot-ews-check reproduce D020": 0,
    "ercot-ews-check examples --invalid": 0,
}


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    meta, body = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S).groups()
    return yaml.safe_load(meta), body


def commands(body):
    return [
        line.strip()
        for block in re.findall(r"```sh\n(.*?)```", body, re.S)
        for line in block.splitlines()
        if line.strip()
    ]


def is_install(command):
    return command.startswith(("python3 -m venv", ".venv/"))


def test_one_skill():
    assert len(SKILLS) == 1


def test_frontmatter_follows_the_spec():
    for path in SKILLS:
        meta, body = frontmatter(path)
        name = meta["name"]
        assert name == path.parent.name
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
        assert 0 < len(meta["description"]) <= 1024
        assert len(meta.get("compatibility", "")) <= 500
        assert len(body.splitlines()) < 500


def test_every_command_runs_with_its_expected_status():
    tool = shutil.which("ercot-ews-check", path=sysconfig.get_path("scripts"))
    assert tool, "install the package first: python -m pip install -e '.[dev]'"
    for path in SKILLS:
        found = [c for c in commands(frontmatter(path)[1]) if not is_install(c)]
        assert sorted(found) == sorted(EXPECTED)
        for command in found:
            argv = [tool, *shlex.split(command)[1:]]
            argv = [EXAMPLE if a == "path/to/document.xml" else a for a in argv]
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
            assert result.returncode == EXPECTED[command], (command, result.stderr)
            assert "Traceback" not in result.stderr, (command, result.stderr)
            assert result.stdout.strip(), command


def test_install_line_names_this_repository():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    url = re.search(r'^Source = "([^"]+)"', pyproject, re.M).group(1)
    for path in SKILLS:
        install = [c for c in commands(frontmatter(path)[1]) if "pip install" in c]
        assert install == [f'.venv/bin/python -m pip install "git+{url}"']


@pytest.mark.network
@pytest.mark.skipif(os.name == "nt", reason="the skill's paths are POSIX; Windows is noted inline")
def test_install_steps_work_from_an_empty_folder(tmp_path):
    """The skill's install lines, with this checkout in place of the GitHub URL."""
    for path in SKILLS:
        for command in [c for c in commands(frontmatter(path)[1]) if is_install(c)]:
            argv = shlex.split(command)
            argv = [str(ROOT) if a.startswith("git+") else a for a in argv]
            if argv[0] == "python3":
                argv[0] = sys.executable
            subprocess.run(argv, cwd=tmp_path, check=True, capture_output=True)
    version = subprocess.run(
        [str(tmp_path / ".venv" / "bin" / "ercot-ews-check"), "--version"],
        capture_output=True,
        text=True,
    )
    assert version.returncode == 0 and "ercot-ews-check" in version.stdout


def test_referenced_files_exist():
    for path in SKILLS:
        _, body = frontmatter(path)
        for ref in re.findall(r"\]\(([^)#]+)\)", body):
            assert (path.parent / ref).is_file(), ref
