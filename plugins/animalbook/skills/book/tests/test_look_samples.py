"""The sample sheets planning.md opens before asking about the look."""

import struct

from conftest import SKILL_DIR

LOOK = SKILL_DIR / "assets" / "look"


def png_size(path):
    """Width and height from the PNG header."""
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def test_sheets_exist_and_planning_points_to_them():
    planning = (SKILL_DIR / "references" / "planning.md").read_text()
    for name in ("covers.png", "callouts.png"):
        assert (LOOK / name).stat().st_size > 10_000
        assert f"assets/look/{name}" in planning


def test_each_sheet_shows_what_its_name_says():
    # Three covers side by side are wider than tall; three callout styles
    # stacked are taller than wide. A copy of one sheet under the other's
    # name fails here.
    covers_w, covers_h = png_size(LOOK / "covers.png")
    callouts_w, callouts_h = png_size(LOOK / "callouts.png")
    assert covers_w > covers_h
    assert callouts_h > callouts_w
    assert (LOOK / "covers.png").read_bytes() != (LOOK / "callouts.png").read_bytes()
