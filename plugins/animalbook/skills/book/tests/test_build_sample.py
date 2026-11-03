"""Build the sample book with the style and check the result."""

import pytest
from conftest import build_sample, latex_problems, pdfinfo


def test_sample_builds_clean(tmp_path):
    pdf, log = build_sample(tmp_path)
    assert latex_problems(log) == []
    assert "504 x 661.68 pts" in pdfinfo(pdf)


@pytest.mark.parametrize("style", ["tinted", "icon", "strip"])
def test_sample_builds_clean_with_each_callout_style(tmp_path, style):
    pdf, log = build_sample(tmp_path, callouts=style)
    assert latex_problems(log) == []
    assert pdf.is_file()
