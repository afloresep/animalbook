"""Turn a video or audio recording into text a book can be written from.

Writes into `--out` (default: `<recording>.prepared/` next to the recording):

- `transcript.vtt`: the transcript with timestamps. A `.vtt` next to the
  recording with the same name (a Teams or Zoom export) is used as is;
  otherwise whisper.cpp makes one on this machine with a 5-bit copy of Whisper
  large-v3-turbo (`setup_env.sh --whisper`).
- `recording.md`: the transcript split into sections. With `--slides`, one
  section per stretch of time a slide of the PDF was on screen ("Slide 7,
  12:30-15:10"). Without it, one section per screen change, each pointing to a
  capture in `frames/`.

Screen changes and slide matches are found on small grayscale samples, one per
second, of the area `--crop` names. A new screen counts only when it differs
from the last one kept and then stays still for a few seconds, so a person
talking or moving on camera does not count as a change.

A transcript from an earlier run is reused; `--retranscribe` makes a new one
(after changing `--language`, or when the recording changed).

Usage:
    python3 prepare_recording.py <recording> --preview [--out DIR]   # one frame, to choose --crop
    python3 prepare_recording.py <recording> [--out DIR] [--slides deck.pdf] [--crop W:H:X:Y]
        [--language es] [--retranscribe]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from check_deps import GET_WHISPER_MODEL, WHISPER_MODEL

_CROP = re.compile(r"\d+:\d+:\d+:\d+")

# Samples are this small: enough to tell slides apart, cheap to compare in pure Python.
SAMPLE_W, SAMPLE_H = 64, 36
# Slides of one template (same title bar, same bullet layout) differ by less than the
# noise of a video frame at 64x36; at 128x72 they are told apart.
SLIDE_W, SLIDE_H = 128, 72
# Distances are mean absolute differences of normalized pixels (0 = identical).
CHANGE = 0.35  # a new screen differs from the last kept one at least this much
STILL = 0.15  # a screen is still while it differs from itself less than this
STILL_SECONDS = 3  # how long a new screen must stay still to count
MATCH = 0.6  # a sample farther than this from every slide shows no slide
TIE = 0.05  # slides this close to the best match tie; of consecutive ones the latest wins (builds)
MIN_SEGMENT = 3  # shorter slide stretches are flicker and join the previous one


@dataclass(frozen=True)
class Cue:
    """One transcript cue: start and end in seconds, and its text."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Segment:
    """A stretch of the recording: seconds [start, end) and what was on screen."""

    start: int
    end: int
    slide: int | None = None  # 1-based PDF page
    frame: str | None = None  # capture path relative to the output folder


# ---------- transcript ----------

_TIME = re.compile(r"((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})")
_VOICE = re.compile(r"<v(?:\.[^ >]*)?\s+([^>]+)>")
_TAG = re.compile(r"<[^>]+>")


def _seconds(stamp: str) -> float:
    parts = [float(p) for p in stamp.replace(",", ".").split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def parse_vtt(text: str) -> list[Cue]:
    """Read the cues of a WebVTT file, keeping speaker names as "Name: text".

    Teams marks speakers with `<v Name>...</v>`; other tags are dropped.
    """
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            match = _TIME.search(line)
            if not match:
                continue
            body = " ".join(lines[i + 1:])
            body = _VOICE.sub(lambda m: m.group(1).strip() + ": ", body)
            body = re.sub(r"\s+", " ", _TAG.sub("", body)).strip()
            if body:
                cues.append(Cue(_seconds(match.group(1)), _seconds(match.group(2)), body))
            break
    return cues


def _no_whisper() -> str:
    """Say how to get a transcript on this platform when no Whisper is installed."""
    first = "no speech-to-text tool found. Export the transcript as a .vtt next to the recording, or "
    if sys.platform == "darwin":
        return first + "run setup_env.sh --whisper (about 0.6 GB)"
    return first + f"install whisper.cpp (whisper-cli) and its model: {GET_WHISPER_MODEL}"


def transcribe(recording: Path, out_dir: Path, language: str | None,
               retranscribe: bool = False) -> tuple[Path, str]:
    """Return the recording's transcript and where it came from, making one if none exists.

    A `.vtt` exported with the recording wins. Otherwise whisper.cpp writes to
    a `-part` file that becomes `transcript.vtt` only when it finishes, so an
    interrupted run never leaves a transcript that looks complete.
    """
    target = out_dir / "transcript.vtt"
    exported = recording.with_suffix(".vtt")
    if exported.exists():
        shutil.copyfile(exported, target)
        return target, "exported with the recording"
    if target.exists() and not retranscribe:
        return target, "made with Whisper in an earlier run (--retranscribe makes a new one)"
    if not shutil.which("whisper-cli"):
        raise SystemExit(_no_whisper())
    if not WHISPER_MODEL.exists():
        get = "setup_env.sh --whisper" if sys.platform == "darwin" else GET_WHISPER_MODEL
        raise SystemExit(f"whisper.cpp has no model at {WHISPER_MODEL}: {get}")
    # whisper.cpp reads 16 kHz mono WAV only.
    audio = out_dir / "audio.wav"
    part = out_dir / "transcript-part.vtt"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(recording), "-vn", "-ac", "1", "-ar", "16000",
                    str(audio)], check=True)
    try:
        subprocess.run(["whisper-cli", "-m", str(WHISPER_MODEL), "-f", str(audio), "-l", language or "auto",
                        "-ovtt", "-of", str(out_dir / part.stem)], check=True)
    finally:
        audio.unlink(missing_ok=True)
    os.replace(part, target)
    return target, f"made with whisper.cpp ({WHISPER_MODEL.name})"


# ---------- images ----------

def normalize(pixels: bytes) -> list[float]:
    """Scale a grayscale sample to mean 0 and spread 1, so brightness and contrast do not matter."""
    n = len(pixels)
    mean = sum(pixels) / n
    spread = (sum((p - mean) ** 2 for p in pixels) / n) ** 0.5
    if spread < 1:  # a flat image: nothing to scale
        return [0.0] * n
    return [(p - mean) / spread for p in pixels]


def distance(a: list[float], b: list[float]) -> float:
    """Mean absolute difference of two normalized samples."""
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def has_video(recording: Path) -> bool:
    """Return whether the recording has a real video stream.

    `V` (capital) leaves out attached pictures, such as the cover art of an MP3.
    """
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "V", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(recording)], capture_output=True, text=True, check=True)
    return bool(out.stdout.strip())


def duration(recording: Path) -> float:
    """Return the recording's length in seconds, or 0 when ffprobe cannot tell."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(recording)], capture_output=True, text=True, check=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def sample_video(recording: Path, crop: str | None, width: int = SAMPLE_W,
                 height: int = SAMPLE_H) -> list[list[float]]:
    """Return one normalized grayscale sample per second of the recording."""
    filters = ["fps=1"] + ([f"crop={crop}"] if crop else []) + [f"scale={width}:{height}", "format=gray"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(recording), "-map", "0:V:0", "-vf", ",".join(filters),
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    size = width * height
    return [normalize(raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)]


def sample_slides(pdf: Path, work: Path, width: int = SLIDE_W, height: int = SLIDE_H) -> list[list[float]]:
    """Return one normalized grayscale sample per page of a PDF."""
    shutil.rmtree(work, ignore_errors=True)  # pages of an earlier, different PDF
    work.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-gray", "-scale-to-x", str(width), "-scale-to-y", str(height),
                    str(pdf), str(work / "page")], check=True)
    return [normalize(_read_pgm(page)) for page in sorted(work.glob("page*.pgm"))]


def _read_pgm(path: Path) -> bytes:
    """Return the pixels of a binary (P5) PGM file."""
    data = path.read_bytes()
    fields, pos = [], 0
    while len(fields) < 4:  # magic, width, height, maxval; skips comments
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            pos = data.index(b"\n", pos)
            continue
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        fields.append(data[pos:end])
        pos = end
    if fields[0] != b"P5":
        raise ValueError(f"{path} is not a binary PGM")
    return data[pos + 1:pos + 1 + int(fields[1]) * int(fields[2])]


# ---------- screen changes ----------

def screen_changes(samples: list[list[float]]) -> list[int]:
    """Return the seconds where a new screen appears and then stays still."""
    kept: list[int] = []
    last = None
    for t, sample in enumerate(samples):
        if last is not None and distance(sample, last) <= CHANGE:
            continue
        ahead = samples[t + 1:t + 1 + STILL_SECONDS]
        if len(ahead) == STILL_SECONDS and all(distance(sample, s) < STILL for s in ahead):
            kept.append(t)
            last = sample
    return kept


def match_slides(samples: list[list[float]], slides: list[list[float]]) -> list[int | None]:
    """Return, per second, the 1-based slide on screen, or None when no slide matches."""
    matches: list[int | None] = []
    for sample in samples:
        distances = [distance(sample, slide) for slide in slides]
        best = min(distances)
        if best > MATCH:
            matches.append(None)
            continue
        # Build-up slides are consecutive pages that differ by one bullet: of the pages
        # that tie in a row from the best one, the latest wins. A page further on that
        # only shares the template (same title bar, same bullets layout) does not.
        page = distances.index(best)
        while page + 1 < len(distances) and distances[page + 1] <= best + TIE:
            page += 1
        matches.append(page + 1)
    return matches


def slide_segments(matches: list[int | None]) -> list[Segment]:
    """Group per-second slide matches into stretches, folding short flickers into the previous one."""
    runs: list[list] = []
    for t, slide in enumerate(matches):
        if runs and runs[-1][0] == slide:
            runs[-1][2] = t + 1
        else:
            runs.append([slide, t, t + 1])
    merged: list[list] = []
    for run in runs:
        if merged and (run[2] - run[1] < MIN_SEGMENT or merged[-1][0] == run[0]):
            merged[-1][2] = run[2]
        else:
            merged.append(run)
    return [Segment(start, end, slide=slide) for slide, start, end in merged]


def capture_times(samples: list[list[float]], changes: list[int]) -> list[int]:
    """Return, per screen change, the last still second that still shows its screen.

    A slide that builds up is complete at the end of its stretch, not at its
    start. The end itself can already show the next slide animating in, which the
    change detection counts only once it stays still: a capture must look more
    like its own screen than like the next one.

    Known limit: samples are one second apart, so a flicker shorter than a
    second (an overlay shown for a fraction of a second) can land exactly on the
    capture without showing in the samples.
    """
    ends = changes[1:] + [len(samples)]
    times = []
    for start, end in zip(changes, ends):
        own, following = samples[start], samples[end] if end < len(samples) else None

        def fits(t: int) -> bool:
            if distance(samples[t], samples[t - 1]) >= STILL:
                return False
            return following is None or distance(samples[t], own) < distance(samples[t], following)

        t = end - 1
        while t > start and not fits(t):
            t -= 1
        times.append(t)
    return times


def change_segments(changes: list[int], length: int, frames: list[str]) -> list[Segment]:
    """Turn screen-change seconds into stretches, each with its capture."""
    starts, frames = list(changes), list(frames)
    if not starts or starts[0] != 0:  # the opening seconds, before the first still screen
        starts.insert(0, 0)
        frames.insert(0, None)
    ends = starts[1:] + [length]
    return [Segment(s, e, frame=f) for s, e, f in zip(starts, ends, frames)]


def save_frames(recording: Path, starts: list[int], seconds: list[int], out_dir: Path) -> list[str]:
    """Save a full-size capture at each second, named by its stretch's start, and return
    their paths relative to out_dir."""
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for start, t in zip(starts, seconds):
        name = f"frames/{_clock(start).replace(':', '-')}.png"
        # Sample t is the frame at t s exactly; later can already be the next slide.
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(recording),
                        "-map", "0:V:0", "-frames:v", "1", str(out_dir / name)], check=True)
        paths.append(name)
    return paths


# ---------- output ----------

def _clock(seconds: float) -> str:
    seconds = int(seconds)
    h, rest = divmod(seconds, 3600)
    return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60:02d}:{rest % 60:02d}"


def write_markdown(recording: Path, cues: list[Cue], segments: list[Segment], source: str,
                   with_slides: bool = False) -> str:
    """Return recording.md: the transcript under one heading per segment."""
    lines = [f"# Recording {recording.stem}", "", f"Source: `{recording.name}`. Transcript: {source}.", ""]
    for segment in segments:
        span = f"{_clock(segment.start)}-{_clock(segment.end)}"
        if segment.slide is not None:
            lines.append(f"## Slide {segment.slide}, {span}")
        elif segment.frame is not None:
            lines.append(f"## {span}, screen `{segment.frame}`")
        else:
            lines.append(f"## {span}" + (", no slide on screen" if with_slides else ""))
        lines.append("")
        for cue in cues:
            if segment.start <= cue.start < segment.end or (segment is segments[-1] and cue.start >= segment.end):
                lines.append(f"[{_clock(cue.start)}] {cue.text}")
        lines.append("")
    return "\n".join(lines)


def crop_box(value: str) -> str:
    """Accept a crop box written as W:H:X:Y in pixels, the only form ffmpeg gets."""
    if not _CROP.fullmatch(value):
        raise argparse.ArgumentTypeError(f"--crop must be W:H:X:Y in pixels, for example 1280:720:0:0, not {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("recording", type=Path)
    parser.add_argument("--slides", type=Path, help="PDF of the slides shown in the recording")
    parser.add_argument("--crop", type=crop_box, help="area of the frame that shows the slides or screen, as W:H:X:Y")
    parser.add_argument("--language", help="spoken language for Whisper, for example es or en")
    parser.add_argument("--out", type=Path, help="output folder (default: <recording>.prepared next to it)")
    parser.add_argument("--retranscribe", action="store_true", help="make a new transcript even if one exists")
    parser.add_argument("--preview", action="store_true", help="save one frame to choose --crop, and stop")
    args = parser.parse_args()

    recording = args.recording.resolve()
    if not recording.is_file():
        raise SystemExit(f"no such recording: {recording}")
    out_dir = (args.out or recording.with_name(recording.name + ".prepared")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    video = has_video(recording)
    if args.preview:
        if not video:
            print("audio only: no screen to crop, run without --crop")
            return 0
        preview = out_dir / "preview.png"
        # One minute in shows the slides on most recordings; a short one gets its middle.
        at = min(60.0, duration(recording) / 2)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.1f}", "-i", str(recording),
                        "-map", "0:V:0", "-frames:v", "1", str(preview)], check=True)
        if not preview.exists() or preview.stat().st_size == 0:
            raise SystemExit(f"ffmpeg saved no frame at {at:.1f} s of {recording.name}")
        print(preview)
        return 0

    transcript, source = transcribe(recording, out_dir, args.language, args.retranscribe)
    cues = parse_vtt(transcript.read_text(errors="replace"))
    if not cues:
        print(f"warning: {transcript} has no text; check the recording has speech, or --retranscribe",
              file=sys.stderr)

    length = int(cues[-1].end) + 1 if cues else 0
    segments: list[Segment] = []
    if video:
        if args.slides:
            samples = sample_video(recording, args.crop, SLIDE_W, SLIDE_H)
            slides = sample_slides(args.slides, out_dir / "slide-samples")
            segments = slide_segments(match_slides(samples, slides))
        else:
            samples = sample_video(recording, args.crop)
            changes = screen_changes(samples)
            frames = save_frames(recording, changes, capture_times(samples, changes), out_dir)
            segments = change_segments(changes, len(samples), frames)
    if not segments:  # audio only, or a video too short to sample: keep the whole transcript
        segments = [Segment(0, length)]

    markdown = write_markdown(recording, cues, segments, source, with_slides=bool(args.slides))
    (out_dir / "recording.md").write_text(markdown)
    print(out_dir / "recording.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
