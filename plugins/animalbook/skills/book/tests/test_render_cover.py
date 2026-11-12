"""Tests for filling the cover template."""

import dataclasses
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import SAMPLE, SKILL_DIR, replace_cover

import render_cover
import setup_book

MOCKUP_ANIMAL = Path(__file__).parent / "fixtures" / "animal.png"

LONG_TITLE = "Activation-Based Monitoring of Reward Hacking in Coding Agents"


def test_long_title_gets_smaller_type():
    short = render_cover.title_size("The Sample Book", "modern")
    long = render_cover.title_size(LONG_TITLE, "modern")
    assert long < short


@pytest.fixture
def book_dir(tmp_path):
    """A book folder with the style and an animal picture in place."""
    setup_book.copy_style(tmp_path)
    (tmp_path / "cover").mkdir()
    shutil.copy(MOCKUP_ANIMAL, tmp_path / "cover" / "animal.png")
    return tmp_path


def test_no_ribbon_when_empty(book_dir):
    html = render_cover.fill_cover(replace_cover(SAMPLE, ribbon=""), book_dir)
    assert 'class="ribbon"' not in html


def test_credit_line_printed_when_given(book_dir):
    html = render_cover.fill_cover(SAMPLE, book_dir)
    assert "CC BY 4.0" in html


def test_title_is_escaped(book_dir):
    html = render_cover.fill_cover(dataclasses.replace(SAMPLE, title="R & D <notes>"), book_dir)
    assert "R &amp; D &lt;notes&gt;" in html


def _darkest(png: Path, crop: str) -> float:
    """Return the darkest intensity (0 black, 1 white) in a crop of a PNG."""
    # ImageMagick 7 rejects `minima.intensity`; on a gray image `minima` is the same value.
    out = subprocess.run(["convert", str(png), "-crop", crop, "+repage", "-colorspace", "Gray",
                          "-format", "%[fx:minima]", "info:"], capture_output=True, text=True, check=True)
    return float(out.stdout)


def _rendered(tmp_path: Path, settings) -> tuple[Path, Path]:
    """Render the cover of a prepared book folder and return (pdf, png)."""
    html_path = tmp_path / "cover" / "cover.html"
    html_path.write_text(render_cover.fill_cover(settings, tmp_path))
    pdf, png = tmp_path / "cover" / "cover.pdf", tmp_path / "cover" / "cover.png"
    render_cover.render(html_path, pdf, png)
    return pdf, png


def test_cover_with_ribbon_prints_full_size_with_footer(book_dir):
    pdf, png = _rendered(book_dir, replace_cover(SAMPLE, ribbon="Working draft"))
    page = book_dir / "page.png"
    subprocess.run(["pdftoppm", "-r", "96", "-png", "-singlefile", str(pdf), str(page.with_suffix(""))], check=True)
    assert _darkest(page, "672x60+0+800") < 0.5
    assert _darkest(png, "672x60+0+800") < 0.5


def test_missing_font_or_image_stops_the_cover(tmp_path):
    with pytest.raises(FileNotFoundError, match="animal.png"):
        render_cover.fill_cover(SAMPLE, tmp_path)


def test_cover_uses_no_viewer_effects(book_dir):
    html = render_cover.fill_cover(SAMPLE, book_dir)
    assert "mix-blend-mode" not in html
    assert "mask-image" not in html


def test_prepared_art_is_transparent_at_the_edges(tmp_path):
    out = tmp_path / "art.png"
    render_cover.prepare_art(MOCKUP_ANIMAL, out)
    corner = subprocess.run(["convert", str(out), "-format", "%[fx:p{0,0}.a]", "info:"],
                            capture_output=True, text=True, check=True).stdout
    assert float(corner) == 0.0
