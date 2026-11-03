"""Load, check and save a book's settings file, `book.json`.

`book.json` sits next to the book's `book.tex` and is the single source for the
book's look and progress: title, fonts, callout style, cover, where meeting
history goes, which parts are written, and the last build.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

LAYOUTS = ("classic", "modern", "block")
CALLOUT_STYLES = ("tinted", "icon", "strip")
SERIFS = ("EB Garamond", "Cormorant Garamond", "Libre Caslon Display")
SANS = ("IBM Plex Sans Condensed", "Fira Sans Condensed")
MONO = "IBM Plex Mono"
HISTORY = ("appendix", "callouts", "both", "none")
PART_STATUS = ("planned", "written")

# family -> style -> file name in assets/fonts/. Filled when the fonts are bundled.
FONT_FILES: dict[str, dict[str, str]] = {}


class SettingsError(ValueError):
    """Raised when book.json is missing a key or holds a value the skill does not support."""


@dataclass(frozen=True)
class Cover:
    """The cover settings.

    Attributes:
        layout: One of LAYOUTS.
        color: The cover's accent color as "#rrggbb".
        tagline: Short line printed at the top (classic) or as the subtitle line.
        ribbon: Text of the corner ribbon; empty for no ribbon.
        image: Path of the animal picture, relative to the book folder.
        image_credit: Credit line the image license asks for; empty when none.
    """

    layout: str
    color: str
    tagline: str
    ribbon: str
    image: str
    image_credit: str


@dataclass(frozen=True)
class BookSettings:
    """Everything the skill records about one book.

    Attributes:
        title: Book title.
        subtitle: One-line subtitle.
        author: Name printed on the cover and title pages.
        imprint: Short imprint name printed where a publisher logo would go.
        serif: Body font, one of SERIFS.
        sans: Heading font, one of SANS.
        callouts: Callout style, one of CALLOUT_STYLES.
        cover: Cover settings.
        history: Where meeting history goes, one of HISTORY.
        parts: Planned parts, each {"title": ..., "status": "planned" | "written"}.
        last_build: {"date": ..., "commit": ...} of the last build, or None.
    """

    title: str
    subtitle: str
    author: str
    imprint: str
    serif: str
    sans: str
    callouts: str
    cover: Cover
    history: str
    parts: list[dict[str, str]] = field(default_factory=list)
    last_build: dict[str, str] | None = None


def _require(data: dict, key: str, where: str = "") -> object:
    """Return data[key] or raise a SettingsError naming the full key."""
    if key not in data:
        raise SettingsError(f"{where}{key}: missing")
    return data[key]


def _choice(value: object, allowed: tuple[str, ...], key: str) -> str:
    """Return value if it is one of allowed, else raise a SettingsError listing them."""
    if value not in allowed:
        raise SettingsError(f"{key}: got '{value}', expected one of {', '.join(allowed)}")
    return str(value)


def from_dict(data: dict) -> BookSettings:
    """Build and check settings from parsed JSON.

    Args:
        data: The parsed content of book.json.

    Returns:
        The checked settings.

    Raises:
        SettingsError: If a key is missing or a value is not supported. The
            message names the key and, for choices, the allowed values.
    """
    cover_data = _require(data, "cover")
    cover = Cover(
        layout=_choice(_require(cover_data, "layout", "cover."), LAYOUTS, "cover.layout"),
        color=str(_require(cover_data, "color", "cover.")),
        tagline=str(cover_data.get("tagline", "")),
        ribbon=str(cover_data.get("ribbon", "")),
        image=str(_require(cover_data, "image", "cover.")),
        image_credit=str(cover_data.get("image_credit", "")),
    )
    parts = list(data.get("parts", []))
    for index, part in enumerate(parts):
        _choice(part.get("status"), PART_STATUS, f"parts[{index}].status")
    return BookSettings(
        title=str(_require(data, "title")),
        subtitle=str(data.get("subtitle", "")),
        author=str(_require(data, "author")),
        imprint=str(data.get("imprint", "")),
        serif=_choice(_require(data, "serif"), SERIFS, "serif"),
        sans=_choice(_require(data, "sans"), SANS, "sans"),
        callouts=_choice(_require(data, "callouts"), CALLOUT_STYLES, "callouts"),
        cover=cover,
        history=_choice(data.get("history", "none"), HISTORY, "history"),
        parts=parts,
        last_build=data.get("last_build"),
    )


def load(path: Path) -> BookSettings:
    """Read and check a book.json file.

    Args:
        path: Path of the book.json file.

    Returns:
        The checked settings.

    Raises:
        SettingsError: If the file is not valid JSON or a value is not supported.
        FileNotFoundError: If the file does not exist.
    """
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path}: not valid JSON: {error}") from error
    return from_dict(data)


def save(settings: BookSettings, path: Path) -> None:
    """Write settings to a book.json file, indented for hand editing.

    Args:
        settings: The settings to write.
        path: Destination path.
    """
    path.write_text(json.dumps(asdict(settings), indent=2) + "\n")
