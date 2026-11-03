"""Tests for reading Wikimedia Commons search results."""

import dataclasses
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


def test_download_saves_the_chosen_full_file(tmp_path, monkeypatch):
    cands = commons_search.parse_imageinfo(load_fixture())
    (tmp_path / "candidates.json").write_text(json.dumps([dataclasses.asdict(c) for c in cands]))
    monkeypatch.setattr(commons_search, "fetch", lambda url: b"full image")
    out = commons_search.download_full(tmp_path, 1)
    assert out.read_bytes() == b"full image"
    assert out.name.startswith("full-01")


def test_artist_entities_are_unescaped():
    response = load_fixture()
    page = next(iter(response["query"]["pages"].values()))
    page["imageinfo"][0]["extmetadata"]["Artist"] = {"value": "Smith &amp; Sons"}
    assert commons_search.parse_imageinfo(response)[0].artist == "Smith & Sons"
