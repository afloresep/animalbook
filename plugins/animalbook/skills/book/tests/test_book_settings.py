"""Tests for loading and saving book.json."""

import pytest
from conftest import FONTS_DIR, SAMPLE, SAMPLE_DICT, write_json

import book_settings


def test_round_trip(tmp_path):
    path = tmp_path / "book.json"
    book_settings.save(SAMPLE, path)
    assert book_settings.load(path) == SAMPLE


def test_unknown_layout_names_key_and_allowed_values(tmp_path):
    path = write_json(tmp_path, {**SAMPLE_DICT, "cover": {**SAMPLE_DICT["cover"], "layout": "modrn"}})
    with pytest.raises(book_settings.SettingsError, match=r"cover.layout.*classic, modern, block"):
        book_settings.load(path)


def test_unknown_font_is_rejected(tmp_path):
    path = write_json(tmp_path, {**SAMPLE_DICT, "serif": "Comic Sans"})
    with pytest.raises(book_settings.SettingsError, match="serif"):
        book_settings.load(path)


@pytest.mark.skipif(not FONTS_DIR.is_dir(), reason="fonts are added in Task 3")
def test_every_font_file_exists():
    for styles in book_settings.FONT_FILES.values():
        for name in styles.values():
            assert (FONTS_DIR / name).is_file(), name
