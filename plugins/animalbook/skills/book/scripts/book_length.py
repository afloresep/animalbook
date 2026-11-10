"""Compare how many pages each part of a built book takes with its budget.

Reads `book.toc` from the last build and the page budgets in `book.json`
(`target_pages` for the main chapters, `parts[].pages` for each part). A part
runs from its part page to the next part, the first appendix or the index.
Front matter, appendices and the index do not count toward the target.

Prints one line per part and a total. Exits 1 when a part or the total is more
than 15% over its budget, so the agent cuts before showing the pages; 0
otherwise, also when the book has no budgets yet.

Usage:
    python3 book_length.py <book_dir>
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import book_settings

# A written page holds about this many words, measured on the book's own layout:
# about 490 on a page of plain prose, about 380 on pages with code, tables and
# callouts. Plans turn page budgets into word budgets with it.
WORDS_PER_PAGE = 400
# Over by more than this share of the budget means cut before showing the pages.
TOLERANCE = 0.15

_ENTRY = re.compile(r"\\contentsline \{(part|chapter)\}\{(.*)\}\{([^{}]*)\}\{[^{}]*\}%?\s*$")
_NUMBERLINE = re.compile(r"\\numberline \{([^{}]*)\}")


@dataclass(frozen=True)
class Span:
    """A part or chapter as built: its title from the contents, first page,
    page count, and for a part its chapters."""

    title: str
    first: int
    pages: int
    chapters: tuple[Span, ...] = ()


def _clean(title: str) -> str:
    """Strip LaTeX from a contents title: the part numeral, spacing and commands."""
    title = re.sub(r"^[IVXLC]+\\hspace\s*\{[^{}]*\}", "", title)
    title = _NUMBERLINE.sub("", title)
    title = re.sub(r"\\[a-zA-Z]+\s*\{([^{}]*)\}", r"\1", title)  # \emph{x} -> x
    title = re.sub(r"\\[a-zA-Z]+\s*", "", title)
    return re.sub(r"\s+", " ", title.replace("{", "").replace("}", "")).strip()


def read_toc(text: str) -> tuple[list[Span], int | None, int | None]:
    """Return the parts of the main matter and where the main matter starts and ends.

    Args:
        text: The content of book.toc.

    Returns:
        (parts, start, end): each part with its chapters; start is the first
        page of the main matter (its first part or numbered chapter); end is
        the first page after it, the first appendix chapter or unnumbered
        back-matter chapter (the index). Either is None when the contents do
        not show it; the last part is left out when end is None. A part runs
        to the next part, a chapter to the next chapter or part.
    """
    entries: list[tuple[str, str, int]] = []  # (kind, title, first page) in the main matter
    end = None
    for line in text.splitlines():
        match = _ENTRY.match(line.strip())
        if not match or not match.group(3).isdigit():
            continue  # front matter has roman page numbers
        kind, title, page = match.group(1), match.group(2), int(match.group(3))
        number = _NUMBERLINE.search(title)
        if kind == "chapter" and (number is None or number.group(1).isalpha()):
            if entries:  # an unnumbered or appendix chapter after the main matter ends it
                end = page
                break
            continue
        entries.append((kind, _clean(title), page))
    start = entries[0][2] if entries else None

    def until(index: int, stop_kinds: tuple[str, ...]) -> int | None:
        later = [page for kind, _, page in entries[index + 1:] if kind in stop_kinds]
        return later[0] if later else end

    parts = []
    for index, (kind, title, first) in enumerate(entries):
        if kind != "part":
            continue
        last = until(index, ("part",))
        if last is None:
            continue
        chapters = []
        for offset, (sub_kind, sub_title, sub_first) in enumerate(entries[index + 1:], index + 1):
            if sub_kind == "part":
                break
            sub_last = until(offset, ("part", "chapter"))
            if sub_last is not None:
                chapters.append(Span(sub_title, sub_first, sub_last - sub_first))
        parts.append(Span(title, first, last - first, tuple(chapters)))
    return parts, start, end


def _over(pages: int, budget: int | None) -> bool:
    return budget is not None and pages > budget * (1 + TOLERANCE)


def _line(title: str, pages: int, budget: int | None, cut: bool) -> str:
    """Return one report line: pages against the budget, and whether it is over."""
    if budget is None:
        return f"{title}: {pages} pages, no budget"
    status = "ok"
    if _over(pages, budget):
        status = f"over by {pages - budget} ({round(100 * (pages - budget) / budget)}%)" + (": cut" if cut else "")
    return f"{title}: {pages} pages, budget {budget}, {status}"


def report(settings: book_settings.BookSettings, parts: list[Span], total: int) -> tuple[list[str], bool]:
    """Return the report lines and whether a part or the whole book is over budget.

    Parts and chapters are matched with book.json by order: the contents list
    them in book order, as book.json does. A chapter over its budget is shown
    so the agent knows where to cut, but only parts and the total decide.
    """
    lines, any_over = [], False
    for index, span in enumerate(parts):
        planned = settings.parts[index] if index < len(settings.parts) else {}
        budget = planned.get("pages")
        any_over |= _over(span.pages, budget)
        lines.append(_line(span.title, span.pages, budget, cut=True))
        chapter_budgets = [chapter.get("pages") for chapter in planned.get("chapters", [])]
        for number, chapter in enumerate(span.chapters):
            chapter_budget = chapter_budgets[number] if number < len(chapter_budgets) else None
            lines.append("  " + _line(chapter.title, chapter.pages, chapter_budget, cut=False))
    any_over |= _over(total, settings.target_pages)
    lines.append(_line("main chapters", total, settings.target_pages, cut=True))
    return lines, any_over


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 book_length.py <book_dir>", file=sys.stderr)
        return 2
    book_dir = Path(sys.argv[1])
    toc = book_dir / "book.toc"
    if not toc.exists():
        print(f"{toc} not found: build the book first", file=sys.stderr)
        return 2
    settings = book_settings.load(book_dir / "book.json")
    parts, start, end = read_toc(toc.read_text(errors="replace"))
    if start is None or end is None:
        print("the contents show no end of the main chapters (an appendix or the index): "
              "keep \\printindex in book.tex to measure the book", file=sys.stderr)
        return 2
    lines, over = report(settings, parts, end - start)
    print("\n".join(lines))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
