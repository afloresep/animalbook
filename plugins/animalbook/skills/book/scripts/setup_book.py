"""Copy the book style into a book folder and write its options from book.json.

Each book keeps its own copy of the style, fonts and icons in `<book>/style/`,
so it builds without the skill and keeps building when the skill changes.
Running this again refreshes `style/` and never touches the book's own files.

Usage:
    python3 setup_book.py <book_dir>
"""

import shutil
import sys
from pathlib import Path

import book_settings
from book_settings import BookSettings

SKILL_DIR = Path(__file__).resolve().parents[1]
STYLE_SOURCES = {
    "animalbook.sty": SKILL_DIR / "tex" / "animalbook.sty",
    "fonts": SKILL_DIR / "assets" / "fonts",
    "icons": SKILL_DIR / "assets" / "icons",
}


def copy_style(book_dir: Path) -> None:
    """Replace `book_dir/style/` with the skill's style file, fonts and icons.

    Args:
        book_dir: The book folder (the one holding book.tex).

    Raises:
        FileNotFoundError: If a part of the skill's style is missing.
        FileExistsError: If `book_dir/style/` exists but was not written by this
            script (it has no animalbook.sty), so replacing it could delete the
            user's files.
    """
    for source in STYLE_SOURCES.values():
        if not source.exists():
            raise FileNotFoundError(f"skill style is incomplete, missing {source}")
    style_dir = book_dir / "style"
    if style_dir.exists() and not (style_dir / "animalbook.sty").is_file():
        raise FileExistsError(
            f"{style_dir} exists and was not made by setup_book.py; move it away first"
        )
    if style_dir.exists():
        shutil.rmtree(style_dir)
    style_dir.mkdir(parents=True)
    for name, source in STYLE_SOURCES.items():
        if source.is_dir():
            shutil.copytree(source, style_dir / name)
        else:
            shutil.copy2(source, style_dir / name)


def _tex_escape(text: str) -> str:
    """Escape the characters that LaTeX treats as special in running text."""
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in text)


FOUR_STYLES = ("regular", "italic", "bold", "bolditalic")


def _font_command(command: str, family: str, styles: tuple[str, ...]) -> str:
    """Return a `\\<command>{file}{file}...` line naming a family's font files in order."""
    files = book_settings.FONT_FILES[family]
    return f"\\{command}" + "".join("{" + files[style] + "}" for style in styles) + "\n"


def write_options(settings: BookSettings, book_dir: Path) -> Path:
    """Write `book_dir/style/options.tex` from the settings.

    Args:
        settings: The book's settings.
        book_dir: The book folder.

    Returns:
        Path of the written options file.
    """
    style_dir = book_dir / "style"
    style_dir.mkdir(parents=True, exist_ok=True)
    meta = "".join(
        "{" + _tex_escape(value) + "}"
        for value in (settings.title, settings.subtitle, settings.author, settings.imprint)
    )
    text = (
        "% Written by setup_book.py from book.json. Edit book.json, not this file.\n"
        f"\\animalbooksetup{{serif={{{settings.serif}}},sans={{{settings.sans}}},"
        f"mono={{{book_settings.MONO}}},callouts={settings.callouts},"
        "fontdir=style/fonts/,icondir=style/icons/}\n"
        f"\\animalbookmeta{meta}\n"
        + _font_command("animalbookserif", settings.serif, FOUR_STYLES)
        + _font_command("animalbooksans", settings.sans, FOUR_STYLES + ("semibold",))
        + _font_command("animalbookmono", book_settings.MONO, FOUR_STYLES)
    )
    out = style_dir / "options.tex"
    out.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    """Set up the book folder given on the command line."""
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    book_dir = Path(sys.argv[1]).resolve()
    settings = book_settings.load(book_dir / "book.json")
    copy_style(book_dir)
    out = write_options(settings, book_dir)
    print(f"style copied to {book_dir / 'style'}, options written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
