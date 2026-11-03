"""Tests for reading Wikimedia Commons search results."""

import json
from pathlib import Path

import pytest

import commons_search

FIXTURE = Path(__file__).parent / "fixtures" / "commons_imageinfo.json"


def load_fixture() -> dict:
    """Return the saved Commons API response."""
    return json.loads(FIXTURE.read_text())


def test_parse_keeps_license_and_urls():
    cands = commons_search.parse_imageinfo(load_fixture())
    owen = next(c for c in cands if "Owen" in c.title)
    assert owen.license == "CC BY 4.0"
    assert owen.file_url.startswith("https://upload.wikimedia.org/")


@pytest.mark.parametrize("name,ok", [
    ("Public domain", True), ("CC0", True), ("CC BY 4.0", True), ("CC BY-SA 3.0", True),
    ("CC BY-ND 4.0", False), ("CC BY-NC 2.0", False), ("Fair use", False), ("", False),
])
def test_usable_licenses(name, ok):
    assert commons_search.is_usable_license(name) is ok


def test_unusable_licenses_are_dropped():
    cands = commons_search.parse_imageinfo(load_fixture())
    assert len(cands) == 2
    assert all(commons_search.is_usable_license(c.license) for c in cands)


def test_fetch_retries_after_too_many_requests(monkeypatch):
    calls = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"image"

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise commons_search.urllib.error.HTTPError(request.full_url, 429, "slow down", {"Retry-After": "0"}, None)
        return Reply()

    monkeypatch.setattr(commons_search.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(commons_search.time, "sleep", lambda seconds: None)
    assert commons_search.fetch("https://upload.wikimedia.org/x.jpg") == b"image"
    assert len(calls) == 2
