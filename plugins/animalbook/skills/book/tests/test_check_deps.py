"""Tests for the dependency check."""

import check_deps
import pytest  # noqa: I001


@pytest.fixture(autouse=True)
def tex_files_present(monkeypatch):
    monkeypatch.setattr(check_deps, "has_tex_file", lambda name: True)


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


def test_missing_luaotfload_is_reported(monkeypatch):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    monkeypatch.setattr(check_deps, "has_tex_file", lambda name: name != "luaotfload-main.lua")
    (item,) = check_deps.check("linux")
    assert item.name == "luaotfload"
    assert item.install == "sudo apt install texlive-luatex"
