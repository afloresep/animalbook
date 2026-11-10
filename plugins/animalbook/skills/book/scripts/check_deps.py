"""Check that every tool and LaTeX package the book skill needs is installed.

Prints one line per missing item with the command that installs it. Exits 1 when
something the book or the cover needs is missing, and 0 when nothing is missing
or only optional items are (Codex, needed only for generated cover animals, and
ffmpeg and Whisper, needed only for recordings). It never installs anything
itself: the user runs the printed commands. On macOS, LaTeX always comes from
setup_env.sh (TinyTeX in ~/.animalbook, no admin rights, a few hundred MB
instead of the 6 GB of MacTeX), and so does everything else when Homebrew is
missing.

Usage:
    python3 check_deps.py
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BOOK = "book build"
COVER = "cover"
GENERATED = "generated engravings"
RECORDINGS = "recordings"
# Missing these does not stop a book: they serve only one optional kind of work.
OPTIONAL = (GENERATED, RECORDINGS)

# setup_env.sh installs everything here, without admin rights; remove_env.sh undoes it.
ENV_BIN = Path.home() / ".animalbook" / "bin"
SETUP = f"bash {Path(__file__).resolve().with_name('setup_env.sh')}"

# command -> (needed for, apt package, macOS command)
COMMANDS: dict[str, tuple[str, str, str]] = {
    "lualatex": (BOOK, "texlive-luatex", SETUP),
    "makeindex": (BOOK, "texlive-binaries", SETUP),
    "pdftoppm": (BOOK, "poppler-utils", "brew install poppler"),
    "pdfinfo": (BOOK, "poppler-utils", "brew install poppler"),
    "convert": (COVER, "imagemagick", "brew install imagemagick"),
    "chromium": (COVER, "chromium", "brew install --cask chromium"),
    "codex": (GENERATED, "", "npm install -g @openai/codex"),
    "ffmpeg": (RECORDINGS, "ffmpeg", "brew install ffmpeg"),
    # Speech to text: whisper-cli (whisper.cpp, light) or mlx_whisper (full) counts.
    "whisper": (RECORDINGS, "", f"{SETUP} --whisper light (about 0.6 GB) or --whisper full (about 3.3 GB)"),
}
WHISPER_NAMES = ("whisper-cli", "mlx_whisper")
LINUX_WHISPER = "conda install -c conda-forge whisper.cpp, and the model as in setup_env.sh --whisper light"

# On macOS without Homebrew (often without admin rights too): command -> what to run instead.
WITHOUT_BREW: dict[str, str] = {
    "pdftoppm": SETUP,
    "pdfinfo": SETUP,
    "convert": SETUP,
    "chromium": "install Google Chrome",
    "ffmpeg": f"{SETUP} --whisper light",
}

# LaTeX package -> Debian/Ubuntu package that ships it
LATEX_PACKAGES: dict[str, str] = {
    "fontspec": "texlive-luatex",
    "titlesec": "texlive-latex-extra",
    "tcolorbox": "texlive-latex-extra",
    "enumitem": "texlive-latex-extra",
    "imakeidx": "texlive-latex-extra",
    "pdfpages": "texlive-latex-recommended",
    "listings": "texlive-latex-recommended",
    "fancyhdr": "texlive-latex-recommended",
    "caption": "texlive-latex-recommended",
    "xcolor": "texlive-latex-recommended",
    "tikz": "texlive-pictures",
}

# LuaLaTeX loads fonts through luaotfload, which Debian ships apart from fontspec.
LUAOTFLOAD_FILE = "luaotfload-main.lua"

# Any of these draws the cover; render_cover.py uses the same list.
CHROMIUM_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
# Chrome works in place of Chromium on macOS.
MAC_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


@dataclass(frozen=True)
class Missing:
    """One missing dependency.

    Attributes:
        name: The command or LaTeX package name.
        kind: "command" or "latex".
        needed_for: What fails without it: "book build", "cover" or
            "generated engravings".
        install: The shell command that installs it on this platform.
    """

    name: str
    kind: str
    needed_for: str
    install: str


def has_tex_file(name: str) -> bool:
    """Return whether kpsewhich finds a file on the TeX search path.

    Args:
        name: File name with its extension, for example "titlesec.sty".

    Returns:
        True when kpsewhich prints a path for it.
    """
    if shutil.which("kpsewhich") is None:
        return False
    result = subprocess.run(["kpsewhich", name], capture_output=True, text=True, check=False)
    return bool(result.stdout.strip())


def has_latex_package(name: str) -> bool:
    """Return whether kpsewhich finds `<name>.sty`.

    Args:
        name: LaTeX package name without the extension.

    Returns:
        True when the package file is on the TeX search path.
    """
    return has_tex_file(f"{name}.sty")


def _has_command(name: str, platform: str) -> bool:
    """Return whether a command is available, counting Chrome for Chromium on macOS."""
    if name == "chromium":
        if any(shutil.which(candidate) for candidate in CHROMIUM_NAMES):
            return True
        return platform == "darwin" and MAC_CHROME.exists()
    if name == "whisper":
        return any(shutil.which(candidate) for candidate in WHISPER_NAMES)
    return shutil.which(name) is not None


def _command_hint(name: str, platform: str) -> str:
    """Return the install command for a missing command on this platform."""
    _, apt_package, mac = COMMANDS[name]
    if platform == "darwin":
        if shutil.which("brew") is None and name in WITHOUT_BREW:
            return WITHOUT_BREW[name]
        return mac
    if name == "whisper":
        return LINUX_WHISPER
    return f"sudo apt install {apt_package}" if apt_package else mac


def _latex_hint_darwin(name: str) -> str:
    """Return the macOS install command for a missing LaTeX package.

    tlmgr comes with every TeX distribution, including setup_env.sh's TinyTeX,
    and installs a package into it; without any TeX, setup_env.sh installs
    TinyTeX with every package the template needs.
    """
    if shutil.which("tlmgr"):
        return f"tlmgr install {name}"
    return SETUP


def check(platform: str) -> list[Missing]:
    """List every missing dependency.

    Args:
        platform: `sys.platform` value; "darwin" gets setup_env.sh for LaTeX and
            Homebrew hints for the rest (setup_env.sh without Homebrew);
            anything else gets apt hints.

    Returns:
        The missing items, commands first, in a fixed order. Empty when
        everything is installed.
    """
    missing = [
        Missing(name, "command", COMMANDS[name][0], _command_hint(name, platform))
        for name in COMMANDS
        if not _has_command(name, platform)
    ]
    if not has_tex_file(LUAOTFLOAD_FILE):
        hint = _latex_hint_darwin("luaotfload") if platform == "darwin" else "sudo apt install texlive-luatex"
        missing.append(Missing("luaotfload", "latex", BOOK, hint))
    for name, apt_package in LATEX_PACKAGES.items():
        if has_latex_package(name):
            continue
        hint = _latex_hint_darwin(name) if platform == "darwin" else f"sudo apt install {apt_package}"
        missing.append(Missing(name, "latex", BOOK, hint))
    return missing


def main() -> int:
    """Print the missing dependencies and return the exit code."""
    if ENV_BIN.is_dir() and str(ENV_BIN) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f'environment installed but not on PATH: export PATH="{ENV_BIN}:$PATH"')
        return 1
    missing = check(sys.platform)
    if not missing:
        print("all dependencies found")
        return 0
    required = [item for item in missing if item.needed_for not in OPTIONAL]
    for item in required:
        print(f"missing {item.kind} {item.name} (needed for {item.needed_for}): {item.install}")
    for item in missing:
        if item.needed_for in OPTIONAL:
            print(f"optional: {item.name} (needed only for {item.needed_for}): {item.install}")
    return 1 if required else 0


if __name__ == "__main__":
    sys.exit(main())
