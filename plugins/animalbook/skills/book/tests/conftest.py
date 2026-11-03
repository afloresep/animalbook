"""Shared test helpers for the book skill."""

import copy
import dataclasses
import shutil
import subprocess
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import book_settings  # noqa: E402

FONTS_DIR = SKILL_DIR / "assets" / "fonts"

SAMPLE_DICT = {
    "title": "The Sample Book",
    "subtitle": "Everything a reader needs to follow the project",
    "author": "A. Author",
    "imprint": "SAMPLE NOTES",
    "serif": "EB Garamond",
    "sans": "IBM Plex Sans Condensed",
    "callouts": "tinted",
    "cover": {
        "layout": "classic",
        "color": "#5b3a7a",
        "tagline": "Notes from one project",
        "ribbon": "Working draft",
        "image": "cover/animal.png",
        "image_credit": "T. Owen, Wellcome Collection, CC BY 4.0",
    },
    "history": "appendix",
    "parts": [{"title": "Foundations", "status": "written"}],
    "last_build": None,
}

SAMPLE = book_settings.from_dict(copy.deepcopy(SAMPLE_DICT))


def write_json(directory: Path, data: dict) -> Path:
    """Write data as book.json in directory and return the path."""
    path = directory / "book.json"
    path.write_text(json.dumps(data))
    return path


def latex_problems(log: str) -> list[str]:
    """Return the error lines and overfull-box warnings of a LaTeX log."""
    return [
        line for line in log.splitlines()
        if line.startswith("!") or line.startswith("Overfull \\hbox")
    ]


def build_sample(tmp_path: Path, callouts: str | None = None) -> tuple[Path, str]:
    """Copy the sample book, set it up like a real book, build it and return (pdf, log)."""
    import setup_book

    book_dir = tmp_path / "book"
    shutil.copytree(SKILL_DIR / "tests" / "sample", book_dir)
    settings = book_settings.load(book_dir / "book.json")
    if callouts is not None:
        settings = dataclasses.replace(settings, callouts=callouts)
    setup_book.copy_style(book_dir)
    setup_book.write_options(settings, book_dir)
    for _ in range(3):
        subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "book.tex"],
            cwd=book_dir, capture_output=True, text=True, check=False,
        )
    return book_dir / "book.pdf", (book_dir / "book.log").read_text(errors="replace")


def pdfinfo(pdf: Path) -> str:
    """Return the output of pdfinfo for a PDF."""
    return subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout


def replace_cover(settings: "book_settings.BookSettings", **fields: str) -> "book_settings.BookSettings":
    """Return settings with some cover fields replaced."""
    return dataclasses.replace(settings, cover=dataclasses.replace(settings.cover, **fields))
