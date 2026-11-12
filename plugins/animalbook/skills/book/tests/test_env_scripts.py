"""Tests for setup_env.sh and remove_env.sh, in a temporary home with stand-in tools.

Every tool the book needs is faked as present, so setup_env.sh must install
nothing: these tests never download anything.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SKILL_DIR

SCRIPTS = SKILL_DIR / "scripts"
MARKER = "# added by animalbook setup_env.sh"
FAKE_UNAME = '#!/bin/sh\ncase "$1" in -s) echo Darwin ;; -m) echo arm64 ;; esac\n'
PRESENT = ("lualatex", "makeindex", "pdftoppm", "pdfinfo", "convert", "chromium")


@pytest.fixture
def home(tmp_path):
    """A temporary home and a PATH holding only stand-ins, this Python and the basic system tools."""
    home = tmp_path / "home"
    fake = tmp_path / "fakebin"
    home.mkdir()
    fake.mkdir()
    (fake / "uname").write_text(FAKE_UNAME)
    (fake / "kpsewhich").write_text('#!/bin/sh\necho "/tex/$1"\n')
    for name in PRESENT:
        (fake / name).write_text("#!/bin/sh\nexit 0\n")
    for script in fake.iterdir():
        script.chmod(0o755)
    (fake / "python3").symlink_to(sys.executable)
    env = {"HOME": str(home), "PATH": f"{fake}:/usr/bin:/bin"}
    return home, env


def _run(script: str, env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPTS / script), *args], env=env, capture_output=True, text=True,
                          timeout=60, check=False)


def test_setup_installs_nothing_when_everything_is_there(home):
    home_dir, env = home
    result = _run("setup_env.sh", env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TinyTeX not needed" in result.stdout
    assert "conda-forge" not in result.stdout
    assert not (home_dir / ".animalbook" / "conda").exists()
    assert not (home_dir / ".mamba").exists()


def test_setup_adds_its_path_line_once(home):
    home_dir, env = home
    _run("setup_env.sh", env)
    _run("setup_env.sh", env)
    assert (home_dir / ".zshrc").read_text().count(MARKER) == 1


@pytest.mark.parametrize("args", [("--video",), ("--whisper",), ("--whisper", "medium")])
def test_setup_rejects_unknown_options(home, args):
    _, env = home
    result = _run("setup_env.sh", env, *args)
    assert result.returncode == 2 and "usage" in result.stderr


def test_whisper_full_needs_apple_silicon(home, tmp_path):
    _, env = home
    (tmp_path / "fakebin" / "uname").write_text('#!/bin/sh\ncase "$1" in -s) echo Darwin ;; -m) echo x86_64 ;; esac\n')
    result = _run("setup_env.sh", env, "--whisper", "full")
    assert result.returncode == 1 and "--whisper light" in result.stderr


def test_remove_keeps_what_is_not_ours(home):
    home_dir, env = home
    env_dir = home_dir / ".animalbook"
    (env_dir / "bin").mkdir(parents=True)
    (home_dir / ".zshrc").write_text(f'alias ll="ls -l"\nexport PATH="{env_dir}/bin:$PATH"  {MARKER}\n')
    conda = home_dir / ".conda"
    conda.mkdir()
    (conda / "environments.txt").write_text(f"/opt/other/env\n{env_dir}/conda\n")
    other_cache = home_dir / ".mamba" / "pkgs" / "urls.txt"
    other_cache.parent.mkdir(parents=True)
    other_cache.write_text("https://example.org/other.conda\n")

    result = _run("remove_env.sh", env)
    assert result.returncode == 0, result.stderr
    assert not env_dir.exists()
    assert (home_dir / ".zshrc").read_text() == 'alias ll="ls -l"\n'
    assert (conda / "environments.txt").read_text() == "/opt/other/env\n"
    assert other_cache.exists()  # another micromamba's cache stays


def test_remove_cleans_up_conda_folder_when_only_ours(home):
    home_dir, env = home
    env_dir = home_dir / ".animalbook"
    env_dir.mkdir()
    (home_dir / ".conda").mkdir()
    (home_dir / ".conda" / "environments.txt").write_text(f"{env_dir}/conda\n")
    assert _run("remove_env.sh", env).returncode == 0
    assert not (home_dir / ".conda").exists()
    assert os.listdir(home_dir) == []
