"""Check that every tool and LaTeX package the book skill needs is installed.

Prints one line per missing item with the command that installs it, and exits 1.
Prints "all dependencies found" and exits 0 when nothing is missing. It never
installs anything itself: the user runs the printed commands.

Usage:
    python3 check_deps.py
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BOOK = "book build"
COVER = "cover"
GENERATED = "generated engravings"

# command -> (needed for, apt package, brew command)
COMMANDS: dict[str, tuple[str, str, str]] = {
    "lualatex": (BOOK, "texlive-luatex", "brew install --cask mactex-no-gui"),
    "makeindex": (BOOK, "texlive-binaries", "brew install --cask mactex-no-gui"),
    "pdftoppm": (BOOK, "poppler-utils", "brew install poppler"),
    "pdfinfo": (BOOK, "poppler-utils", "brew install poppler"),
    "convert": (COVER, "imagemagick", "brew install imagemagick"),
    "chromium": (COVER, "chromium", "brew install --cask chromium"),
    "codex": (GENERATED, "", "npm install -g @openai/codex"),
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


def has_latex_package(name: str) -> bool:
    """Return whether kpsewhich finds `<name>.sty`.

    Args:
        name: LaTeX package name without the extension.

    Returns:
        True when the package file is on the TeX search path.
    """
    if shutil.which("kpsewhich") is None:
        return False
    result = subprocess.run(
        ["kpsewhich", f"{name}.sty"], capture_output=True, text=True, check=False
    )
    return bool(result.stdout.strip())


def _has_command(name: str, platform: str) -> bool:
    """Return whether a command is available, counting Chrome for Chromium on macOS."""
    if shutil.which(name) is not None:
        return True
    return name == "chromium" and platform == "darwin" and MAC_CHROME.exists()


def _command_hint(name: str, platform: str) -> str:
    """Return the install command for a missing command on this platform."""
    _, apt_package, brew = COMMANDS[name]
    if platform == "darwin" or not apt_package:
        return brew
    return f"sudo apt install {apt_package}"


def check(platform: str) -> list[Missing]:
    """List every missing dependency.

    Args:
        platform: `sys.platform` value; "darwin" gets Homebrew and tlmgr hints,
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
    for name, apt_package in LATEX_PACKAGES.items():
        if has_latex_package(name):
            continue
        hint = f"tlmgr install {name}" if platform == "darwin" else f"sudo apt install {apt_package}"
        missing.append(Missing(name, "latex", BOOK, hint))
    return missing


def main() -> int:
    """Print the missing dependencies and return the exit code."""
    missing = check(sys.platform)
    if not missing:
        print("all dependencies found")
        return 0
    for item in missing:
        print(f"missing {item.kind} {item.name} (needed for {item.needed_for}): {item.install}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
