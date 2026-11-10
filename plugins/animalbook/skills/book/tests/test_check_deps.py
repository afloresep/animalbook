"""Tests for the dependency check."""

import check_deps
import pytest  # noqa: I001


@pytest.fixture(autouse=True)
def tex_files_present(monkeypatch):
    monkeypatch.setattr(check_deps, "has_tex_file", lambda name: True)


def test_reports_missing_command_with_install_hint(monkeypatch):
    monkeypatch.setattr(
        check_deps.shutil, "which",
        lambda name: None if name in check_deps.CHROMIUM_NAMES else "/usr/bin/x",
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


def test_only_codex_missing_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name == "codex" else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    assert check_deps.main() == 0
    assert "optional" in capsys.readouterr().out


def test_google_chrome_counts_as_chromium(monkeypatch):
    present = {"google-chrome"}
    monkeypatch.setattr(check_deps.shutil, "which",
                        lambda name: "/usr/bin/x" if name in present or name not in check_deps.CHROMIUM_NAMES else None)
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    assert check_deps.check("linux") == []


def test_environment_off_path_is_reported(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(check_deps, "ENV_BIN", tmp_path)
    monkeypatch.setenv("PATH", "/usr/bin")
    assert check_deps.main() == 1
    assert str(tmp_path) in capsys.readouterr().out


def test_video_tools_are_optional(monkeypatch, capsys):
    monkeypatch.setattr(check_deps.shutil, "which",
                        lambda name: None if name in ("codex", "ffmpeg", "mlx_whisper") else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    assert check_deps.main() == 0
    assert "optional: ffmpeg" in capsys.readouterr().out


def test_macos_without_homebrew_points_to_setup_env(monkeypatch):
    absent = {"brew", "tlmgr", "lualatex"}
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name in absent else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: name != "titlesec")
    hints = {m.name: m.install for m in check_deps.check("darwin")}
    assert "setup_env.sh" in hints["lualatex"] and "setup_env.sh" in hints["titlesec"]


def test_macos_with_homebrew_keeps_homebrew_hints(monkeypatch):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name in ("pdftoppm", "tlmgr") else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: name != "titlesec")
    hints = {m.name: m.install for m in check_deps.check("darwin")}
    assert hints == {"pdftoppm": "brew install poppler", "titlesec": "brew install --cask mactex-no-gui"}
