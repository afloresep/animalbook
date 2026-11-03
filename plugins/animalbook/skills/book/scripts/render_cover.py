"""Fill the cover template from book.json and save it as PDF and PNG with Chromium.

The cover uses the book's own copy of the fonts in `<book>/style/fonts/`, so run
setup_book.py first. Output goes to `<book>/cover/cover.pdf` and `cover.png`.

Usage:
    python3 render_cover.py <book_dir>
"""

import html
import shutil
import subprocess
import sys
from pathlib import Path

import book_settings
from book_settings import BookSettings

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "cover" / "cover.html"

# Cover size in CSS pixels (7 x 9.19 in at 96 px per inch).
WIDTH_PX = 672
HEIGHT_PX = 883

# layout -> (largest title size in px, characters that fit at that size, smallest size).
# Past the character budget the size shrinks in proportion, down to the floor.
TITLE_SIZES: dict[str, tuple[int, int, int]] = {
    "classic": (150, 8, 48),
    "modern": (80, 26, 40),
    "block": (84, 20, 40),
}

# A classic cover puts the last word in the band and the rest above it in italics,
# as "Learning" over "Python"; longer titles go whole into the band.
CLASSIC_SPLIT_MAX_WORDS = 4

CHROMIUM_NAMES = ("chromium", "chromium-browser", "google-chrome")
MAC_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def split_title(title: str, layout: str) -> tuple[str, str]:
    """Split a title into the small kicker line and the main title.

    Args:
        title: The book title.
        layout: The cover layout.

    Returns:
        (kicker, main). The kicker is empty unless the layout is classic and the
        title has between two and CLASSIC_SPLIT_MAX_WORDS words.
    """
    words = title.split()
    if layout == "classic" and 1 < len(words) <= CLASSIC_SPLIT_MAX_WORDS:
        return " ".join(words[:-1]), words[-1]
    return "", title


def title_size(title: str, layout: str) -> int:
    """Return the font size in px for the main title on a cover.

    Args:
        title: The book title, before splitting.
        layout: The cover layout.

    Returns:
        The size in px; smaller for longer titles, never below the layout's floor.
    """
    largest, budget, floor = TITLE_SIZES[layout]
    main = split_title(title, layout)[1]
    if len(main) <= budget:
        return largest
    return max(floor, int(largest * budget / len(main)))


def _title_html(settings: BookSettings, main: str, image_url: str) -> str:
    """Return the title, subtitle and animal markup in the order the layout needs."""
    title = f'<div class="title">{html.escape(main)}</div>'
    subtitle = f'<div class="subtitle">{html.escape(settings.subtitle)}</div>'
    art = f'<div class="art"><img src="{image_url}" alt=""></div>'
    if settings.cover.layout == "block":
        return f'{art}<div class="titleblock">{title}{subtitle}</div>'
    return f"{title}{subtitle}{art}"


def fill_cover(settings: BookSettings, book_dir: Path) -> str:
    """Fill the cover template.

    Args:
        settings: The book's settings.
        book_dir: The book folder; fonts and the image are read from it.

    Returns:
        The cover as an HTML document.
    """
    cover = settings.cover
    kicker, main = split_title(settings.title, cover.layout)
    serif = book_settings.FONT_FILES[settings.serif]
    sans = book_settings.FONT_FILES[settings.sans]
    ribbon = "<br>".join(html.escape(line) for line in cover.ribbon.splitlines())
    in_bar = cover.layout in ("modern", "block")
    values = {
        "layout": cover.layout,
        "color": cover.color,
        "title": html.escape(settings.title),
        "title_size": str(title_size(settings.title, cover.layout)),
        "title_html": _title_html(settings, main, (book_dir / cover.image).resolve().as_uri()),
        "kicker": html.escape(kicker),
        "tagline": html.escape(cover.tagline),
        "author": html.escape(settings.author),
        "imprint": html.escape(settings.imprint),
        "imprint_in_bar": html.escape(settings.imprint) if in_bar else "",
        "ribbon_html": f'<div class="ribbon">{ribbon}</div>' if ribbon else "",
        "credit_html": (
            f'<div class="credit">Cover image: {html.escape(cover.image_credit)}</div>'
            if cover.image_credit else ""
        ),
        "fontdir": (book_dir / "style" / "fonts").resolve().as_uri(),
        "serif_regular": serif["regular"],
        "serif_italic": serif["italic"],
        "sans_regular": sans["regular"],
        "sans_semibold": sans["semibold"],
        "sans_bold": sans["bold"],
    }
    text = TEMPLATE.read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def find_chromium() -> str:
    """Return the Chromium or Chrome executable.

    Raises:
        FileNotFoundError: If neither is installed.
    """
    for name in CHROMIUM_NAMES:
        path = shutil.which(name)
        if path:
            return path
    if MAC_CHROME.exists():
        return str(MAC_CHROME)
    raise FileNotFoundError("Chromium or Chrome is needed for the cover; run check_deps.py")


def render(html_path: Path, pdf_out: Path, png_out: Path) -> None:
    """Save an HTML cover as a one-page PDF and a PNG preview.

    Args:
        html_path: The filled cover HTML.
        pdf_out: Destination of the PDF.
        png_out: Destination of the PNG.

    Raises:
        FileNotFoundError: If Chromium is missing.
        subprocess.CalledProcessError: If Chromium fails.
    """
    chromium = find_chromium()
    common = [chromium, "--headless", "--disable-gpu", "--allow-file-access-from-files",
              "--hide-scrollbars", "--force-color-profile=srgb"]
    url = html_path.resolve().as_uri()
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={pdf_out}", url],
                   check=True, capture_output=True)
    subprocess.run(common + [f"--window-size={WIDTH_PX},{HEIGHT_PX}", f"--screenshot={png_out}", url],
                   check=True, capture_output=True)


def main() -> int:
    """Render the cover of the book folder given on the command line."""
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    book_dir = Path(sys.argv[1]).resolve()
    settings = book_settings.load(book_dir / "book.json")
    out_dir = book_dir / "cover"
    out_dir.mkdir(exist_ok=True)
    html_path = out_dir / "cover.html"
    html_path.write_text(fill_cover(settings, book_dir))
    render(html_path, out_dir / "cover.pdf", out_dir / "cover.png")
    print(f"cover written to {out_dir / 'cover.pdf'} and {out_dir / 'cover.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
