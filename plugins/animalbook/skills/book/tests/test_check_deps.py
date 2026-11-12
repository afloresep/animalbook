"""Tests for the dependency check."""

import re

import check_deps
import pytest  # noqa: I001
from conftest import SKILL_DIR


@pytest.fixture(autouse=True)
def tex_files_present(monkeypatch, tmp_path):
    monkeypatch.setattr(check_deps, "has_tex_file", lambda name: True)
    # Never read this machine's ~/.animalbook.
    monkeypatch.setattr(check_deps, "ENV_BIN", tmp_path / "no-env" / "bin")


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


def test_environment_off_path_is_noted_and_checked(monkeypatch, tmp_path, capsys):
    env_bin = tmp_path / "bin"
    env_bin.mkdir()
    monkeypatch.setattr(check_deps, "ENV_BIN", env_bin)
    monkeypatch.setenv("PATH", "/usr/bin")
    seen_paths = []
    monkeypatch.setattr(check_deps.shutil, "which",
                        lambda name: seen_paths.append(check_deps.os.environ["PATH"]) or "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    assert check_deps.main() == 0  # an interrupted setup no longer hides the real report
    assert f'export PATH="{env_bin}:$PATH"' in capsys.readouterr().out
    assert seen_paths[0].startswith(str(env_bin))


def test_video_tools_are_optional(monkeypatch, capsys):
    monkeypatch.setattr(check_deps.sys, "platform", "darwin")
    absent = {"codex", "ffmpeg", "ffprobe", *check_deps.WHISPER_NAMES}
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name in absent else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    assert check_deps.main() == 0
    out = capsys.readouterr().out
    assert "optional, only for recordings:" in out and "brew install ffmpeg" in out
    assert "--whisper light" in out


def test_either_whisper_counts_but_whisper_cpp_needs_its_model(monkeypatch, tmp_path):
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    model = tmp_path / "model.bin"
    monkeypatch.setattr(check_deps, "LIGHT_MODEL", model)
    for present in check_deps.WHISPER_NAMES:
        monkeypatch.setattr(check_deps.shutil, "which",
                            lambda name, p=present: None if name in check_deps.WHISPER_NAMES and name != p else "/x")
        missing = [m.name for m in check_deps.check("darwin")]
        assert missing == (["whisper"] if present == "whisper-cli" else [])
    model.write_bytes(b"")
    assert check_deps.check("darwin") == []


def test_plan_joins_commands_and_runs_setup_last(monkeypatch):
    setup = check_deps.SETUP
    items = [
        check_deps.Missing("lualatex", "command", "book build", setup),
        check_deps.Missing("pdftoppm", "command", "book build", "brew install poppler"),
        check_deps.Missing("pdfinfo", "command", "book build", "brew install poppler"),
        check_deps.Missing("convert", "command", "cover", "brew install imagemagick"),
        check_deps.Missing("ffmpeg", "command", "recordings", f"{setup} --recordings"),
        check_deps.Missing("titlesec", "latex", "book build", setup),
    ]
    assert check_deps.plan(items) == [
        ("brew install poppler imagemagick", ["pdftoppm", "pdfinfo", "convert"]),
        (f"{setup} --recordings", ["lualatex", "ffmpeg", "titlesec"]),
    ]


def test_linux_gets_one_apt_line(monkeypatch):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None)
    monkeypatch.setattr(check_deps, "has_tex_file", lambda name: False)
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: False)
    required = [m for m in check_deps.check("linux") if m.needed_for not in check_deps.OPTIONAL]
    (command, names), = check_deps.plan(required)
    assert command.startswith("sudo apt install texlive-luatex texlive-binaries poppler-utils")
    assert "fontspec" in names and "chromium" in names


def test_tex_with_tlmgr_installs_its_own_missing_commands(monkeypatch):
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name == "makeindex" else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: True)
    (item,) = check_deps.check("darwin")
    assert item.install == "tlmgr install makeindex"  # not setup_env.sh, which skips an existing TeX


def test_chrome_for_this_user_only_counts(monkeypatch, tmp_path):
    chrome = tmp_path / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"
    chrome.parent.mkdir(parents=True)
    chrome.write_text("")
    monkeypatch.setattr(check_deps, "MAC_CHROMES", (tmp_path / "absent", chrome))
    assert check_deps.find_mac_chrome() == chrome


def test_setup_path_is_quoted_for_the_shell():
    assert check_deps.SETUP.startswith("bash ")
    assert check_deps.shlex.split(check_deps.SETUP)[1].endswith("setup_env.sh")


def test_every_package_of_the_style_is_checked_and_installed():
    sty = (SKILL_DIR / "tex" / "animalbook.sty").read_text()
    required = {name.strip() for group in re.findall(r"\\RequirePackage(?:\[[^\]]*\])?\{([^}]*)\}", sty)
                for name in group.split(",")}
    assert required <= set(check_deps.LATEX_PACKAGES)
    setup = (SKILL_DIR / "scripts" / "setup_env.sh").read_text()
    tlmgr_line = setup[setup.index('"$TLMGR" install'):].split('"$TLMGR" option')[0]
    installed = set(tlmgr_line.replace("\\", " ").split())
    for tlmgr_package, _ in check_deps.LATEX_PACKAGES.values():
        assert tlmgr_package in installed, tlmgr_package


def test_macos_without_homebrew_points_to_setup_env(monkeypatch):
    absent = {"brew", "tlmgr", "lualatex"}
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name in absent else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: name != "titlesec")
    hints = {m.name: m.install for m in check_deps.check("darwin")}
    assert "setup_env.sh" in hints["lualatex"] and "setup_env.sh" in hints["titlesec"]


def test_macos_with_homebrew_gets_tinytex_not_mactex(monkeypatch):
    absent = {"pdftoppm", "tlmgr", "lualatex"}
    monkeypatch.setattr(check_deps.shutil, "which", lambda name: None if name in absent else "/usr/bin/x")
    monkeypatch.setattr(check_deps, "has_latex_package", lambda name: name != "titlesec")
    hints = {m.name: m.install for m in check_deps.check("darwin")}
    assert hints == {"lualatex": check_deps.SETUP, "pdftoppm": "brew install poppler", "titlesec": check_deps.SETUP}
    assert not any("mactex" in hint for hint in hints.values())
