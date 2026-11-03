"""Shared test helpers for the book skill."""

import copy
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
