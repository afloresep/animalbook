"""Tests for filling the cover template."""

import dataclasses

from conftest import SAMPLE, replace_cover

import render_cover

LONG_TITLE = "Activation-Based Monitoring of Reward Hacking in Coding Agents"


def test_long_title_gets_smaller_type():
    short = render_cover.title_size("The Sample Book", "modern")
    long = render_cover.title_size(LONG_TITLE, "modern")
    assert long < short


def test_no_ribbon_when_empty(tmp_path):
    html = render_cover.fill_cover(replace_cover(SAMPLE, ribbon=""), tmp_path)
    assert 'class="ribbon"' not in html


def test_credit_line_printed_when_given(tmp_path):
    html = render_cover.fill_cover(SAMPLE, tmp_path)
    assert "CC BY 4.0" in html


def test_title_is_escaped(tmp_path):
    html = render_cover.fill_cover(dataclasses.replace(SAMPLE, title="R & D <notes>"), tmp_path)
    assert "R &amp; D &lt;notes&gt;" in html
