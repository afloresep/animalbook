"""Tests for measuring each part of a built book against its page budget."""

import dataclasses
import shutil
import subprocess
import sys

import book_length
import pytest
from conftest import SAMPLE, SKILL_DIR, build_sample

TOC = r"""\contentsline {chapter}{Conventions Used in This Book}{v}{chapter*.2}%
\contentsline {part}{I\hspace {1em}Foundations}{1}{part.1}%
\contentsline {chapter}{\numberline {1}Probes and Steering}{3}{chapter.1}%
\contentsline {section}{\numberline {1.1}What a Probe Is}{6}{section.1.1}%
\contentsline {chapter}{\numberline {2}Sparse Autoencoders}{12}{chapter.2}%
\contentsline {part}{II\hspace {1em}What We \emph {Found}}{21}{part.2}%
\contentsline {chapter}{\numberline {3}Results}{23}{chapter.3}%
\contentsline {chapter}{\numberline {A}Timeline}{41}{appendix.A}%
\contentsline {chapter}{Index}{47}{section*.5}%
"""


def _settings(target, *budgets):
    parts = [{"title": f"Part {i}", "status": "written", "pages": b} for i, b in enumerate(budgets)]
    return dataclasses.replace(SAMPLE, target_pages=target, parts=parts)


def test_parts_run_to_the_next_part_and_stop_at_the_appendix():
    parts, start, end = book_length.read_toc(TOC)
    assert [(p.title, p.first, p.pages) for p in parts] == [("Foundations", 1, 20), ("What We Found", 21, 20)]
    assert [(c.title, c.pages) for c in parts[0].chapters] == [("Probes and Steering", 9), ("Sparse Autoencoders", 9)]
    assert [(c.title, c.pages) for c in parts[1].chapters] == [("Results", 18)]
    assert (start, end) == (1, 41)  # front matter (roman pages), the appendix and the index do not count


def test_within_tolerance_is_ok_and_beyond_it_is_cut():
    parts, start, end = book_length.read_toc(TOC)
    lines, over = book_length.report(_settings(40, 18, 20), parts, end - start)
    assert not over and lines[0].endswith("ok")  # 20 pages on a budget of 18 is 11% over
    lines, over = book_length.report(_settings(40, 15, 20), parts, end - start)
    assert over and "over by 5 (33%): cut" in lines[0]


def test_whole_book_over_target_is_cut():
    parts, start, end = book_length.read_toc(TOC)
    lines, over = book_length.report(_settings(30, 20, 20), parts, end - start)
    assert over and lines[-1] == "main chapters: 40 pages, budget 30, over by 10 (33%): cut"


def test_chapter_over_budget_is_shown_but_the_part_decides():
    parts, start, end = book_length.read_toc(TOC)
    settings = _settings(40, 20, 20)
    settings.parts[0]["chapters"] = [{"title": "Probes", "pages": 5}, {"title": "SAEs", "pages": 13}]
    lines, over = book_length.report(settings, parts, end - start)
    assert not over
    assert "  Probes and Steering: 9 pages, budget 5, over by 4 (80%)" in lines


def test_book_without_budgets_only_reports():
    parts, start, end = book_length.read_toc(TOC)
    lines, over = book_length.report(dataclasses.replace(SAMPLE, target_pages=None), parts, end - start)
    assert not over and lines[-1] == "main chapters: 40 pages, no budget"


def test_book_without_parts_counts_its_chapters():
    toc = "\n".join(line for line in TOC.splitlines() if "{part}" not in line)
    parts, start, end = book_length.read_toc(toc)
    assert parts == [] and (start, end) == (3, 41)


def test_page_budget_must_be_a_whole_number():
    import book_settings
    from conftest import SAMPLE_DICT
    for bad in (0, -5, 12.5, "80", True):
        with pytest.raises(book_settings.SettingsError, match="target_pages"):
            book_settings.from_dict({**SAMPLE_DICT, "target_pages": bad})
    with pytest.raises(book_settings.SettingsError, match=r"parts\[0\].pages"):
        book_settings.from_dict({**SAMPLE_DICT, "parts": [{"title": "A", "status": "planned", "pages": 0}]})
    chapters = [{"title": "Intro", "pages": "3"}]
    with pytest.raises(book_settings.SettingsError, match=r"parts\[0\].chapters\[0\].pages"):
        book_settings.from_dict({**SAMPLE_DICT, "parts": [{"title": "A", "status": "planned", "chapters": chapters}]})
    with pytest.raises(book_settings.SettingsError, match=r"parts\[0\].page: unknown key"):
        book_settings.from_dict({**SAMPLE_DICT, "parts": [{"title": "A", "status": "planned", "page": 9}]})


@pytest.mark.skipif(shutil.which("lualatex") is None, reason="needs LuaLaTeX")
def test_measures_the_built_sample(tmp_path):
    pdf, _ = build_sample(tmp_path)
    result = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "book_length.py"), str(pdf.parent)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Foundations: ") and "main chapters:" in result.stdout
