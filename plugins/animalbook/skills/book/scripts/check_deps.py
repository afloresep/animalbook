"""Check that every tool and LaTeX package the book skill needs is installed.

Prints an install plan: the fewest commands that install what is missing, in
the order to run them, each with the items it covers. Exits 1 when something
the book or the cover needs is missing, and 0 when nothing is missing or only
optional items are (Codex, needed only for generated cover animals, and ffmpeg
and Whisper, needed only for recordings). It never installs anything itself:
the user runs the printed commands.

On macOS, LaTeX always comes from setup_env.sh (TinyTeX in ~/.animalbook, no
admin rights, a few hundred MB instead of the 6 GB of MacTeX), and so does
everything else when Homebrew is missing.

Usage:
    python3 check_deps.py
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BOOK = "book build"
COVER = "cover"
GENERATED = "generated engravings"
RECORDINGS = "recordings"
TRANSCRIBE = "recordings without a .vtt transcript"
# Missing these does not stop a book: they serve only one optional kind of work.
OPTIONAL = (GENERATED, RECORDINGS, TRANSCRIBE)

# setup_env.sh installs everything here, without admin rights; remove_env.sh undoes it.
ENV_DIR = Path.home() / ".animalbook"
ENV_BIN = ENV_DIR / "bin"
SETUP = f"bash {shlex.quote(str(Path(__file__).resolve().with_name('setup_env.sh')))}"

# whisper.cpp needs this model file; prepare_recording.py reads it from the same place.
WHISPER_MODEL = ENV_DIR / "models" / "ggml-large-v3-turbo-q5_0.bin"
WHISPER_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
GET_WHISPER_MODEL = f"curl -L --create-dirs -o {shlex.quote(str(WHISPER_MODEL))} {WHISPER_MODEL_URL}"

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
    "ffprobe": (RECORDINGS, "ffmpeg", "brew install ffmpeg"),
    # Speech to text: whisper.cpp (whisper-cli) with its model file.
    "whisper": (TRANSCRIBE, "", f"{SETUP} --whisper"),
}
LINUX_WHISPER = f"install whisper.cpp (whisper-cli), then {GET_WHISPER_MODEL}"

# On macOS, a TeX that has tlmgr installs its own missing commands: command -> tlmgr package.
TEX_COMMANDS = {"lualatex": "luatex", "makeindex": "makeindex"}

# On macOS without Homebrew (often without admin rights too): command -> what to run instead.
WITHOUT_BREW: dict[str, str] = {
    "pdftoppm": SETUP,
    "pdfinfo": SETUP,
    "convert": SETUP,
    "chromium": "install Google Chrome (into ~/Applications if you have no admin rights)",
    "ffmpeg": f"{SETUP} --recordings",
    "ffprobe": f"{SETUP} --recordings",
}

# Every \RequirePackage of tex/animalbook.sty, plus TikZ, which tcolorbox's skins
# load: .sty name -> (TeX Live package for tlmgr, Debian/Ubuntu package).
# texlive-latex-extra depends on texlive-latex-recommended and texlive-latex-base,
# so it brings in every package marked with it here.
LATEX_PACKAGES: dict[str, tuple[str, str]] = {
    "iftex": ("iftex", "texlive-latex-extra"),
    "geometry": ("geometry", "texlive-latex-extra"),
    "amsmath": ("amsmath", "texlive-latex-extra"),
    "amssymb": ("amsfonts", "texlive-latex-extra"),
    "fontspec": ("fontspec", "texlive-luatex"),
    "microtype": ("microtype", "texlive-latex-recommended"),
    "xcolor": ("xcolor", "texlive-latex-recommended"),
    "graphicx": ("graphics", "texlive-latex-extra"),
    "booktabs": ("booktabs", "texlive-latex-recommended"),
    "tabularx": ("tools", "texlive-latex-extra"),
    "longtable": ("tools", "texlive-latex-extra"),
    "array": ("tools", "texlive-latex-extra"),
    "titlesec": ("titlesec", "texlive-latex-extra"),
    "fancyhdr": ("fancyhdr", "texlive-latex-recommended"),
    "caption": ("caption", "texlive-latex-recommended"),
    "listings": ("listings", "texlive-latex-recommended"),
    "enumitem": ("enumitem", "texlive-latex-extra"),
    "tcolorbox": ("tcolorbox", "texlive-latex-extra"),
    "imakeidx": ("imakeidx", "texlive-latex-extra"),
    "pdfpages": ("pdfpages", "texlive-latex-recommended"),
    "etoolbox": ("etoolbox", "texlive-latex-extra"),
    "hyperref": ("hyperref", "texlive-latex-extra"),
    "tikz": ("pgf", "texlive-pictures"),
}

# LuaLaTeX loads fonts through luaotfload, which Debian ships apart from fontspec.
LUAOTFLOAD_FILE = "luaotfload-main.lua"

# Any of these draws the cover; render_cover.py uses the same lists.
CHROMIUM_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
# Chrome works in place of Chromium on macOS, installed for everyone or only for this user.
_CHROME_APP = Path("Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
MAC_CHROMES = (Path("/") / _CHROME_APP, Path.home() / _CHROME_APP)

# Commands whose arguments can be joined into one call, in the order to run them.
# setup_env.sh runs last, so it does not install through conda what Homebrew is about to.
_JOINABLE = ("brew install --cask ", "brew install ", "sudo apt install ", "tlmgr install ", "npm install -g ")
# setup_env.sh options from least to most: each one installs everything the ones before do.
_SETUP_LEVELS = ("", " --recordings", " --whisper")


@dataclass(frozen=True)
class Missing:
    """One missing dependency.

    Attributes:
        name: The command or LaTeX package name.
        kind: "command" or "latex".
        needed_for: What fails without it: one of BOOK, COVER, GENERATED,
            RECORDINGS or TRANSCRIBE.
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


def find_mac_chrome() -> Path | None:
    """Return Google Chrome's executable on macOS, in /Applications or ~/Applications."""
    return next((path for path in MAC_CHROMES if path.exists()), None)


def _has_command(name: str, platform: str) -> bool:
    """Return whether a command is available, counting Chrome for Chromium on macOS
    and whisper-cli only with its model."""
    if name == "chromium":
        if any(shutil.which(candidate) for candidate in CHROMIUM_NAMES):
            return True
        return platform == "darwin" and find_mac_chrome() is not None
    if name == "whisper":
        return bool(shutil.which("whisper-cli")) and WHISPER_MODEL.exists()
    return shutil.which(name) is not None


def _command_hint(name: str, platform: str) -> str:
    """Return the install command for a missing command on this platform."""
    _, apt_package, mac = COMMANDS[name]
    if platform == "darwin":
        if name in TEX_COMMANDS and shutil.which("tlmgr"):
            return f"tlmgr install {TEX_COMMANDS[name]}"
        if shutil.which("brew") is None and name in WITHOUT_BREW:
            return WITHOUT_BREW[name]
        return mac
    if name == "whisper":
        return GET_WHISPER_MODEL if shutil.which("whisper-cli") else LINUX_WHISPER
    return f"sudo apt install {apt_package}" if apt_package else mac


def _latex_hint_darwin(tlmgr_package: str) -> str:
    """Return the macOS install command for a missing LaTeX package.

    tlmgr comes with every TeX distribution, including setup_env.sh's TinyTeX,
    and installs a package into it; without any TeX, setup_env.sh installs
    TinyTeX with every package the template needs.
    """
    if shutil.which("tlmgr"):
        return f"tlmgr install {tlmgr_package}"
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
    for name, (tlmgr_package, apt_package) in LATEX_PACKAGES.items():
        if has_latex_package(name):
            continue
        hint = _latex_hint_darwin(tlmgr_package) if platform == "darwin" else f"sudo apt install {apt_package}"
        missing.append(Missing(name, "latex", BOOK, hint))
    return missing


def plan(items: list[Missing]) -> list[tuple[str, list[str]]]:
    """Group missing items into the fewest commands, in the order to run them.

    Args:
        items: Missing items, as `check` returns them.

    Returns:
        (command, names it installs) pairs. Commands that take a list of
        packages (brew, apt, tlmgr) are joined into one call each; setup_env.sh
        appears once, with the largest option any item asks for, and last.
    """
    joined: dict[str, tuple[list[str], list[str]]] = {}
    setup_level, setup_names = -1, []
    others: dict[str, list[str]] = {}
    for item in items:
        if item.install.startswith(SETUP):
            option = item.install[len(SETUP):]
            setup_level = max(setup_level, _SETUP_LEVELS.index(option) if option in _SETUP_LEVELS else 0)
            setup_names.append(item.name)
            continue
        prefix = next((p for p in _JOINABLE if item.install.startswith(p)), None)
        if prefix is None:
            others.setdefault(item.install, []).append(item.name)
            continue
        packages, names = joined.setdefault(prefix, ([], []))
        for package in item.install[len(prefix):].split():
            if package not in packages:
                packages.append(package)
        names.append(item.name)
    steps = [(prefix + " ".join(joined[prefix][0]), joined[prefix][1]) for prefix in _JOINABLE if prefix in joined]
    steps += list(others.items())
    if setup_level >= 0:
        steps.append((SETUP + _SETUP_LEVELS[setup_level], setup_names))
    return steps


def _print_plan(title: str, items: list[Missing]) -> None:
    print(title)
    for command, names in plan(items):
        print(f"  {command}")
        print(f"      installs: {', '.join(names)}")


def main() -> int:
    """Print the install plan for what is missing and return the exit code."""
    path = os.environ.get("PATH", "")
    if ENV_BIN.is_dir() and str(ENV_BIN) not in path.split(os.pathsep):
        # A shell started before setup_env.sh: check with the environment as it will be.
        print(f'note: {ENV_BIN} is not on PATH in this shell. Start each command of the skill with: '
              f'export PATH="{ENV_BIN}:$PATH" &&')
        os.environ["PATH"] = f"{ENV_BIN}{os.pathsep}{path}"
    missing = check(sys.platform)
    if not missing:
        print("all dependencies found")
        return 0
    required = [item for item in missing if item.needed_for not in OPTIONAL]
    optional = [item for item in missing if item.needed_for in OPTIONAL]
    if required:
        _print_plan("missing: run these in order, then check again", required)
    else:
        print("everything the book needs is installed")
    for needed_for in OPTIONAL:
        group = [item for item in optional if item.needed_for == needed_for]
        if group:
            _print_plan(f"optional, only for {needed_for}:", group)
    return 1 if required else 0


if __name__ == "__main__":
    sys.exit(main())
