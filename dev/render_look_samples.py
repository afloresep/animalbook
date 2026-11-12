"""Render the pictures the skill shows before asking about the look of a book.

Writes two sheets into the skill's `assets/look/`:

- `covers.png`: the three cover layouts (classic, modern, block), side by side.
- `callouts.png`: the three callout styles (tinted, icon, strip), one above the other.

Each picture is labeled with the name the question uses. Run it again after a
change to the cover template or the callout styles, from the repository root:

    python3 dev/render_look_samples.py

Needs what a book build needs: LuaLaTeX, Poppler, ImageMagick and Chromium.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "plugins" / "animalbook" / "skills" / "book"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import book_settings  # noqa: E402
import setup_book  # noqa: E402

OUT_DIR = SKILL_DIR / "assets" / "look"
ANIMAL = SKILL_DIR / "tests" / "fixtures" / "animal.png"
LABEL_FONT = SKILL_DIR / "assets" / "fonts" / "IBMPlexSansCondensed-SemiBold.ttf"
COVER_COLOR = "#2f5d62"
LAYOUTS = book_settings.LAYOUTS
CALLOUT_STYLES = book_settings.CALLOUT_STYLES

BOOK = {
    "title": "Your Project",
    "subtitle": "What the project does and why",
    "author": "A. Author",
    "imprint": "PROJECT NOTES",
    "serif": "EB Garamond",
    "sans": "IBM Plex Sans Condensed",
    "callouts": "tinted",
    "cover": {"layout": "classic", "color": COVER_COLOR, "tagline": "Notes from one project",
              "ribbon": "Working draft", "image": "cover/animal.png", "image_credit": ""},
    "history": "none",
    "parts": [],
    "last_build": None,
}

CALLOUT_PAGE = r"""\documentclass[10pt]{book}
\usepackage{style/animalbook}
\input{style/options.tex}
\pagestyle{empty}
\begin{document}
\keyidea{The one thing the reader must remember from this section, in a
sentence or two.}

\careful{The mistake a reader is likely to make here, and how to avoid it.}

\questionsfor{the team}{An open question the book cannot answer yet.}
\end{document}
"""


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True)


def book_dir(work: Path, name: str, **changes: object) -> Path:
    """Make a book folder with the style, the animal and a book.json."""
    folder = work / name
    (folder / "cover").mkdir(parents=True)
    shutil.copy(ANIMAL, folder / "cover" / "animal.png")
    data = json.loads(json.dumps(BOOK))
    data["cover"].update(changes.pop("cover", {}))
    data.update(changes)
    (folder / "book.json").write_text(json.dumps(data))
    settings = book_settings.load(folder / "book.json")
    setup_book.copy_style(folder)
    setup_book.write_options(settings, folder)
    return folder


def label(image: Path, text: str, out: Path) -> None:
    """Add a white band with the label above the picture."""
    run(["convert", str(image), "-background", "white", "-gravity", "northwest", "-splice", "0x70",
         "-font", str(LABEL_FONT), "-pointsize", "40", "-fill", "#222222", "-annotate", "+0+14", text,
         "-bordercolor", "white", "-border", "24", str(out)])


def sheet(images: list[Path], out: Path, across: bool) -> None:
    """Put labeled pictures side by side (across) or one above the other, on white."""
    size, join = ("x900", "+append") if across else ("1400x", "-append")
    run(["convert", *map(str, images), "-resize", size, "-background", "white", "-gravity", "north",
         join, "-bordercolor", "white", "-border", "16", "-strip", str(out)])


def covers(work: Path) -> list[Path]:
    labeled = []
    for layout in LAYOUTS:
        folder = book_dir(work, f"cover-{layout}", cover={"layout": layout})
        run([sys.executable, str(SKILL_DIR / "scripts" / "render_cover.py"), str(folder)])
        out = work / f"cover-{layout}.png"
        run(["convert", str(folder / "cover" / "cover.png"), "-bordercolor", "#cccccc", "-border", "2", str(out)])
        label(out, layout.capitalize(), out)
        labeled.append(out)
    return labeled


def callouts(work: Path) -> list[Path]:
    labeled = []
    for style in CALLOUT_STYLES:
        folder = book_dir(work, f"callouts-{style}", callouts=style)
        (folder / "page.tex").write_text(CALLOUT_PAGE)
        run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "page.tex"], cwd=folder)
        run(["pdftoppm", "-r", "150", "-png", "-singlefile", "page.pdf", "page"], cwd=folder)
        out = work / f"callouts-{style}.png"
        run(["convert", str(folder / "page.png"), "-trim", "+repage", str(out)])
        label(out, style.capitalize(), out)
        labeled.append(out)
    return labeled


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        sheet(covers(work), OUT_DIR / "covers.png", across=True)
        sheet(callouts(work), OUT_DIR / "callouts.png", across=False)
    for name in ("covers.png", "callouts.png"):
        print(OUT_DIR / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
