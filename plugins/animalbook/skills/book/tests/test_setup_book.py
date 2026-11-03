"""Tests for copying the style into a book and writing its options."""

import pytest
from conftest import SAMPLE

import setup_book


def test_options_tex_carries_the_choices(tmp_path):
    out = setup_book.write_options(SAMPLE, tmp_path)
    text = out.read_text()
    assert "serif={EB Garamond}" in text and "callouts=tinted" in text


def test_rerun_never_touches_book_files(tmp_path):
    (tmp_path / "book.tex").write_text("mine")
    (tmp_path / "book.json").write_text("{}")
    setup_book.copy_style(tmp_path)
    setup_book.copy_style(tmp_path)
    assert (tmp_path / "book.tex").read_text() == "mine"
    assert (tmp_path / "book.json").read_text() == "{}"
    assert (tmp_path / "style" / "animalbook.sty").is_file()


def test_options_tex_names_the_font_files(tmp_path):
    text = setup_book.write_options(SAMPLE, tmp_path).read_text()
    assert "\\animalbookserif{EBGaramond-Regular.otf}{EBGaramond-Italic.otf}" in text
    assert "IBMPlexSansCondensed-SemiBold.ttf" in text
    assert "IBMPlexMono-Regular.ttf" in text


def test_refuses_to_replace_a_style_folder_it_did_not_write(tmp_path):
    (tmp_path / "style").mkdir()
    (tmp_path / "style" / "mine.tex").write_text("hand made")
    with pytest.raises(FileExistsError, match="style"):
        setup_book.copy_style(tmp_path)
    assert (tmp_path / "style" / "mine.tex").read_text() == "hand made"


def test_rerun_keeps_chapters(tmp_path):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "01.tex").write_text("chapter")
    setup_book.copy_style(tmp_path)
    setup_book.write_options(SAMPLE, tmp_path)
    setup_book.copy_style(tmp_path)
    assert (tmp_path / "chapters" / "01.tex").read_text() == "chapter"
