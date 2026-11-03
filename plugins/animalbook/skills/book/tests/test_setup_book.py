"""Tests for copying the style into a book and writing its options."""

import pytest
from conftest import SAMPLE, SKILL_DIR

import setup_book

STY = SKILL_DIR / "tex" / "animalbook.sty"


def test_options_tex_carries_the_choices(tmp_path):
    out = setup_book.write_options(SAMPLE, tmp_path)
    text = out.read_text()
    assert "serif={EB Garamond}" in text and "callouts=tinted" in text


@pytest.mark.skipif(not STY.is_file(), reason="the style is added in Task 4")
def test_rerun_never_touches_book_files(tmp_path):
    (tmp_path / "book.tex").write_text("mine")
    (tmp_path / "book.json").write_text("{}")
    setup_book.copy_style(tmp_path)
    setup_book.copy_style(tmp_path)
    assert (tmp_path / "book.tex").read_text() == "mine"
    assert (tmp_path / "book.json").read_text() == "{}"
    assert (tmp_path / "style" / "animalbook.sty").is_file()
