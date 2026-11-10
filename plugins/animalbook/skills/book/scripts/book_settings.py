"""Load, check and save a book's settings file, `book.json`.

`book.json` sits next to the book's `book.tex` and is the single source for the
book's look and progress: title, fonts, callout style, cover, where meeting
history goes, which parts are written, and the last build.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

LAYOUTS = ("classic", "modern", "block")
CALLOUT_STYLES = ("tinted", "icon", "strip")
SERIFS = ("EB Garamond", "Cormorant Garamond", "Libre Caslon Display")
SANS = ("IBM Plex Sans Condensed", "Fira Sans Condensed")
MONO = "IBM Plex Mono"
HISTORY = ("appendix", "callouts", "both", "none")
PART_STATUS = ("planned", "written")
# A recording is content (a class or talk the book teaches from: it may give
# definitions and numbers) or context (meetings that explain decisions: never numbers).
RECORDING_ROLES = ("content", "context")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# family -> style -> file name in assets/fonts/. Sans families add "semibold" for
# labels. Cormorant's Regular is too light for body text, so Medium stands in.
# Libre Caslon Display has one style only.
FONT_FILES: dict[str, dict[str, str]] = {
    "EB Garamond": {
        "regular": "EBGaramond-Regular.otf",
        "italic": "EBGaramond-Italic.otf",
        "bold": "EBGaramond-Bold.otf",
        "bolditalic": "EBGaramond-BoldItalic.otf",
    },
    "Cormorant Garamond": {
        "regular": "CormorantGaramond-Medium.ttf",
        "italic": "CormorantGaramond-MediumItalic.ttf",
        "bold": "CormorantGaramond-Bold.ttf",
        "bolditalic": "CormorantGaramond-BoldItalic.ttf",
    },
    "Libre Caslon Display": {
        "regular": "LibreCaslonDisplay-Regular.ttf",
        "italic": "LibreCaslonDisplay-Regular.ttf",
        "bold": "LibreCaslonDisplay-Regular.ttf",
        "bolditalic": "LibreCaslonDisplay-Regular.ttf",
    },
    "IBM Plex Sans Condensed": {
        "regular": "IBMPlexSansCondensed-Regular.ttf",
        "italic": "IBMPlexSansCondensed-Italic.ttf",
        "semibold": "IBMPlexSansCondensed-SemiBold.ttf",
        "bold": "IBMPlexSansCondensed-Bold.ttf",
        "bolditalic": "IBMPlexSansCondensed-BoldItalic.ttf",
    },
    "Fira Sans Condensed": {
        "regular": "FiraSansCondensed-Regular.ttf",
        "italic": "FiraSansCondensed-Italic.ttf",
        "semibold": "FiraSansCondensed-SemiBold.ttf",
        "bold": "FiraSansCondensed-Bold.ttf",
        "bolditalic": "FiraSansCondensed-BoldItalic.ttf",
    },
    "IBM Plex Mono": {
        "regular": "IBMPlexMono-Regular.ttf",
        "italic": "IBMPlexMono-Italic.ttf",
        "bold": "IBMPlexMono-Bold.ttf",
        "bolditalic": "IBMPlexMono-Bold.ttf",
    },
}


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
        parts: Planned parts, each {"title": ..., "status": "planned" | "written"},
            with an optional "pages" (the part's page budget) and "chapters"
            (its chapters in order, each {"title": ..., "pages": ...}).
        last_build: {"date": ..., "commit": ...} of the last build, or None.
        target_pages: How long the main chapters should be, in pages, or None
            for no target. Front matter, appendices and the index do not count.
        recordings: Groups of recordings and their role, each
            {"path": <file or folder>, "role": "content" | "context"}. Empty
            when the book uses no recordings.
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
    recordings: list[dict[str, str]] = field(default_factory=list)
    target_pages: int | None = None


def _pages(value: object, key: str) -> int | None:
    """Return a page count: a whole number above zero, or None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SettingsError(f"{key}: got '{value}', expected a whole number of pages above zero")
    return value


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


def _reject_unknown(data: dict, allowed: tuple[str, ...], where: str = "") -> None:
    """Raise a SettingsError for the first key that is not one of allowed."""
    for key in data:
        if key not in allowed:
            raise SettingsError(f"{where}{key}: unknown key, expected one of {', '.join(allowed)}")


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
    _reject_unknown(data, tuple(f.name for f in fields(BookSettings)))
    cover_data = _require(data, "cover")
    _reject_unknown(cover_data, tuple(f.name for f in fields(Cover)), "cover.")
    color = str(_require(cover_data, "color", "cover."))
    if not HEX_COLOR.match(color):
        raise SettingsError(f"cover.color: got '{color}', expected a color like #5b3a7a")
    cover = Cover(
        layout=_choice(_require(cover_data, "layout", "cover."), LAYOUTS, "cover.layout"),
        color=color,
        tagline=str(cover_data.get("tagline", "")),
        ribbon=str(cover_data.get("ribbon", "")),
        image=str(_require(cover_data, "image", "cover.")),
        image_credit=str(cover_data.get("image_credit", "")),
    )
    parts = list(data.get("parts", []))
    for index, part in enumerate(parts):
        if not isinstance(part, dict) or "title" not in part:
            raise SettingsError(f'parts[{index}]: expected {{"title": ..., "status": ...}}')
        _choice(part.get("status"), PART_STATUS, f"parts[{index}].status")
        _reject_unknown(part, ("title", "status", "pages", "chapters"), f"parts[{index}].")
        _pages(part.get("pages"), f"parts[{index}].pages")
        for number, chapter in enumerate(part.get("chapters", [])):
            key = f"parts[{index}].chapters[{number}]"
            if not isinstance(chapter, dict) or "title" not in chapter:
                raise SettingsError(f'{key}: expected {{"title": ..., "pages": ...}}')
            _reject_unknown(chapter, ("title", "pages"), f"{key}.")
            _pages(chapter.get("pages"), f"{key}.pages")
    recordings = list(data.get("recordings", []))
    for index, group in enumerate(recordings):
        if not isinstance(group, dict) or not group.get("path"):
            raise SettingsError(f'recordings[{index}]: expected {{"path": ..., "role": "content" | "context"}}')
        _reject_unknown(group, ("path", "role"), f"recordings[{index}].")
        _choice(group.get("role"), RECORDING_ROLES, f"recordings[{index}].role")
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
        recordings=recordings,
        target_pages=_pages(data.get("target_pages"), "target_pages"),
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
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path}: not valid JSON: {error}") from error
    return from_dict(data)


def save(settings: BookSettings, path: Path) -> None:
    """Write settings to a book.json file, indented for hand editing.

    Args:
        settings: The settings to write.
        path: Destination path.
    """
    path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
