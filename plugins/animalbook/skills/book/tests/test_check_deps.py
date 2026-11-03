"""Tests for the dependency check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_deps  # noqa: E402


def test_reports_missing_command_with_install_hint(monkeypatch):
    monkeypatch.setattr(
        check_deps.shutil, "which", lambda name: None if name == "chromium" else "/usr/bin/x"
    )
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    missing = check_deps.check("linux")
    assert [m.name for m in missing] == ["chromium"]
    assert "apt" in missing[0].install


def test_codex_only_needed_for_generated_engravings(monkeypatch):
    monkeypatch.setattr(
        check_deps.shutil, "which", lambda name: None if name == "codex" else "/usr/bin/x"
    )
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    (item,) = check_deps.check("linux")
    assert item.needed_for == "generated engravings"


def test_missing_latex_package_names_the_texlive_package(monkeypatch):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: name != "tcolorbox")
    (item,) = check_deps.check("linux")
    assert "texlive-latex-extra" in item.install
    assert check_deps.check("darwin")[0].install.startswith("tlmgr install")
