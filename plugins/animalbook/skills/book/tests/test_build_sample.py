"""Build the sample book with the style and check the result."""

from conftest import build_sample, latex_problems, pdfinfo


def test_sample_builds_clean(tmp_path):
    pdf, log = build_sample(tmp_path)
    assert latex_problems(log) == []
    assert "504 x 661.68 pts" in pdfinfo(pdf)
