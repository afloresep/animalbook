"""Search Wikimedia Commons for engravings that may go on a book cover.

Lists candidate images with their license, downloads a thumbnail of each into a
folder for the agent to look at, and drops any image whose license forbids
changes or reuse (ND, NC, fair use, unknown).

Usage:
    python3 commons_search.py --query "cuckoo engraving" --out <new empty dir>
    python3 commons_search.py --category "Cuculus canorus in art" --out <new empty dir>
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "animalbook-skill/0.1 (book cover engraving search)"
THUMB_WIDTH = 900
TIMEOUT_S = 30
# Commons throttles quick bursts of thumbnail downloads (HTTP 429).
PAUSE_S = 1.0
RETRIES = 4
TOO_MANY_REQUESTS = 429

# Licenses that allow cropping and whitening an image for a cover.
USABLE = re.compile(r"(?i)^(public domain|pd\b.*|cc0.*|cc[ -]by(-sa)?[ -]\d.*)$")
# Clauses that rule an image out even if the pattern above matched part of it.
FORBIDDEN = re.compile(r"(?i)\b(nd|nc|fair use|all rights reserved)\b")
TAGS = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Candidate:
    """One image found on Commons.

    Attributes:
        title: The file page title, "File:...".
        width: Full image width in pixels.
        height: Full image height in pixels.
        license: Short license name as Commons gives it, for example "CC BY 4.0".
        artist: Artist or source, tags removed.
        date: Date of the original, as free text.
        thumb_url: URL of a thumbnail about THUMB_WIDTH pixels wide.
        file_url: URL of the full image.
        page_url: URL of the file's description page, for the credit line.
    """

    title: str
    width: int
    height: int
    license: str
    artist: str
    date: str
    thumb_url: str
    file_url: str
    page_url: str


def is_usable_license(name: str) -> bool:
    """Return whether a license allows changing the image for a cover.

    Args:
        name: Short license name from Commons.

    Returns:
        True for public domain, CC0, CC BY and CC BY-SA; False for anything with
        ND or NC, fair use, all rights reserved, or an empty name.
    """
    name = name.strip()
    return bool(USABLE.match(name)) and not FORBIDDEN.search(name)


def _meta(info: dict, key: str) -> str:
    """Return one extmetadata value as plain text, or "" when it is missing."""
    value = info.get("extmetadata", {}).get(key, {}).get("value", "")
    return TAGS.sub("", str(value)).strip()


def parse_imageinfo(response: dict) -> list[Candidate]:
    """Turn a Commons API imageinfo response into usable candidates.

    Args:
        response: Parsed JSON of an API call with prop=imageinfo,
            iiprop=url|size|extmetadata and iiurlwidth set.

    Returns:
        Candidates with a usable license, in the order the API returned them.
    """
    candidates = []
    for page in response.get("query", {}).get("pages", {}).values():
        if not page.get("imageinfo"):
            continue
        info = page["imageinfo"][0]
        candidate = Candidate(
            title=page["title"],
            width=int(info.get("width", 0)),
            height=int(info.get("height", 0)),
            license=_meta(info, "LicenseShortName"),
            artist=_meta(info, "Artist"),
            date=_meta(info, "DateTimeOriginal"),
            thumb_url=info.get("thumburl", info.get("url", "")),
            file_url=info.get("url", ""),
            page_url=info.get("descriptionurl", ""),
        )
        if is_usable_license(candidate.license):
            candidates.append(candidate)
    return candidates


def fetch(url: str) -> bytes:
    """Download a URL, waiting and retrying when Commons answers 429.

    Args:
        url: The URL to fetch.

    Returns:
        The response body.

    Raises:
        urllib.error.HTTPError: On any other HTTP error, or on 429 after RETRIES tries.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as reply:
                return reply.read()
        except urllib.error.HTTPError as error:
            if error.code != TOO_MANY_REQUESTS or attempt == RETRIES - 1:
                raise
            time.sleep(float(error.headers.get("Retry-After", 5)) + PAUSE_S * (attempt + 1))
    raise AssertionError("unreachable")


def _get(params: dict[str, str]) -> dict:
    """Call the Commons API and return the parsed JSON."""
    query = urllib.parse.urlencode({"format": "json", **params})
    return json.loads(fetch(f"{API}?{query}"))


IMAGEINFO = {"prop": "imageinfo", "iiprop": "url|size|extmetadata",
             "iiextmetadatafilter": "LicenseShortName|Artist|DateTimeOriginal",
             "iiurlwidth": str(THUMB_WIDTH)}


def search(query: str, limit: int = 20) -> list[Candidate]:
    """Search Commons files by text.

    Args:
        query: Search words, for example "cuckoo engraving".
        limit: Most results to ask for.

    Returns:
        Candidates with a usable license.
    """
    return parse_imageinfo(_get({"action": "query", "generator": "search", "gsrnamespace": "6",
                                 "gsrlimit": str(limit), "gsrsearch": f"{query} filetype:bitmap",
                                 **IMAGEINFO}))


def category(name: str, limit: int = 60) -> list[Candidate]:
    """List the files of a Commons category.

    Args:
        name: Category name without the "Category:" prefix.
        limit: Most files to ask for.

    Returns:
        Candidates with a usable license.
    """
    return parse_imageinfo(_get({"action": "query", "generator": "categorymembers",
                                 "gcmtitle": f"Category:{name}", "gcmtype": "file",
                                 "gcmlimit": str(limit), **IMAGEINFO}))


def download_thumbnails(candidates: list[Candidate], out_dir: Path) -> None:
    """Save each candidate's thumbnail as NN.jpg and the list as candidates.json.

    Args:
        candidates: Candidates to save.
        out_dir: A new, empty folder. Downloads are untrusted data: keep them apart
            from code.

    Raises:
        FileExistsError: If out_dir exists and is not empty.
    """
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} is not empty; give a new folder")
    out_dir.mkdir(parents=True, exist_ok=True)
    for number, candidate in enumerate(candidates, start=1):
        (out_dir / f"{number:02d}.jpg").write_bytes(fetch(candidate.thumb_url))
        time.sleep(PAUSE_S)
    (out_dir / "candidates.json").write_text(json.dumps([asdict(c) for c in candidates], indent=1))


def main() -> int:
    """Run a search from the command line and print the numbered candidates."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query")
    group.add_argument("--category")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    found = search(args.query) if args.query else category(args.category)
    download_thumbnails(found, args.out)
    for number, candidate in enumerate(found, start=1):
        print(f"{number:02d}  {candidate.license:14}  {candidate.width}x{candidate.height}  "
              f"{candidate.title}")
    print(f"{len(found)} candidates; thumbnails and candidates.json in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
