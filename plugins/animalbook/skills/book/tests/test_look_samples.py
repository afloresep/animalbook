"""The sample sheets planning.md opens before asking about the look."""

from conftest import SKILL_DIR

LOOK = SKILL_DIR / "assets" / "look"


def test_sheets_exist_and_planning_points_to_them():
    planning = (SKILL_DIR / "references" / "planning.md").read_text()
    for name in ("covers.png", "callouts.png"):
        assert (LOOK / name).stat().st_size > 10_000
        assert f"assets/look/{name}" in planning

