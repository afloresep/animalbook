"""Turn a video or audio recording into text a book can be written from.

Writes `<recording>.prepared/` next to the recording:

- `transcript.vtt`: the transcript with timestamps. A `.vtt` next to the
  recording with the same name (a Teams or Zoom export) is used as is;
  otherwise Whisper makes one on this machine: mlx-whisper with the full model
  when it is installed (`setup_env.sh --whisper full`), else whisper.cpp with a
  compressed copy of the same model (`setup_env.sh --whisper light`).
- `recording.md`: the transcript split into sections. With `--slides`, one
  section per stretch of time a slide of the PDF was on screen ("Slide 7,
  12:30-15:10"). Without it, one section per screen change, each pointing to a
  capture in `frames/`.

Screen changes and slide matches are found on small grayscale samples, one per
second, of the area `--crop` names. A new screen counts only when it differs
from the last one kept and then stays still for a few seconds, so a person
talking or moving on camera does not count as a change.

Usage:
    python3 prepare_recording.py <recording> --preview          # one frame, to choose --crop
    python3 prepare_recording.py <recording> [--slides deck.pdf] [--crop W:H:X:Y]
        [--language es] [--max-captures-per-hour 240]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ENV_DIR = Path.home() / ".animalbook"
# Full: mlx-whisper, the model from Hugging Face, kept under HF_CACHE by setup_env.sh.
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
HF_CACHE = ENV_DIR / "models" / "hf"
# Light: whisper.cpp (whisper-cli) and the same model compressed to 5 bits, about 0.6 GB.
LIGHT_MODEL = ENV_DIR / "models" / "ggml-large-v3-turbo-q5_0.bin"
NO_WHISPER = ("no speech-to-text tool found: export the transcript as a .vtt next to the "
              "recording, or install one with setup_env.sh --whisper light (or --whisper full)")
_CROP = re.compile(r"\d+:\d+:\d+:\d+")

# Samples are this small: enough to tell slides apart, cheap to compare in pure Python.
SAMPLE_W, SAMPLE_H = 64, 36
# Distances are mean absolute differences of normalized pixels (0 = identical).
CHANGE = 0.35  # a new screen differs from the last kept one at least this much
STILL = 0.15  # a screen is still while it differs from itself less than this
STILL_SECONDS = 3  # how long a new screen must stay still to count
MATCH = 0.6  # a sample farther than this from every slide shows no slide
TIE = 0.05  # slides this close to the best match tie; the later one wins (builds)
MIN_SEGMENT = 3  # shorter slide stretches are flicker and join the previous one
MIN_CAPTURES = 10  # the per-hour limit never cuts a recording below this many
# A guard for odd videos (endless scrolling), not a budget: a talk or class with a
# slide every 40 s reaches 90 an hour, and a lower limit drops real slides.
CAPTURES_PER_HOUR = 240


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


def transcribe(recording: Path, out_dir: Path, language: str | None) -> tuple[Path, str]:
    """Return the recording's transcript and where it came from, making one if none exists.

    A `.vtt` exported with the recording wins. Otherwise mlx-whisper (full) is
    used when installed, else whisper.cpp (light).
    """
    target = out_dir / "transcript.vtt"
    exported = recording.with_suffix(".vtt")
    if exported.exists():
        shutil.copyfile(exported, target)
        return target, "exported with the recording"
    if target.exists():
        return target, "made with Whisper in an earlier run"
    if shutil.which("mlx_whisper"):
        command = ["mlx_whisper", str(recording), "--model", WHISPER_MODEL, "--output-format", "vtt",
                   "--output-dir", str(out_dir), "--output-name", "transcript"]
        if language:
            command += ["--language", language]
        env = dict(os.environ)
        if "HF_HOME" not in env and HF_CACHE.is_dir():  # the model setup_env.sh downloaded
            env["HF_HOME"] = str(HF_CACHE)
        subprocess.run(command, check=True, env=env)
        return target, f"made with mlx-whisper ({WHISPER_MODEL})"
    if shutil.which("whisper-cli"):
        if not LIGHT_MODEL.exists():
            raise SystemExit(f"whisper.cpp has no model at {LIGHT_MODEL}: run setup_env.sh --whisper light")
        # whisper.cpp reads 16 kHz mono WAV only.
        audio = out_dir / "audio.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(recording), "-vn", "-ac", "1", "-ar", "16000",
                        str(audio)], check=True)
        try:
            subprocess.run(["whisper-cli", "-m", str(LIGHT_MODEL), "-f", str(audio), "-l", language or "auto",
                            "-ovtt", "-of", str(out_dir / "transcript")], check=True)
        finally:
            audio.unlink(missing_ok=True)
        return target, f"made with whisper.cpp ({LIGHT_MODEL.name})"
    raise SystemExit(NO_WHISPER)


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


def sample_video(recording: Path, crop: str | None) -> list[list[float]]:
    """Return one normalized grayscale sample per second of the recording."""
    filters = ["fps=1"] + ([f"crop={crop}"] if crop else []) + [f"scale={SAMPLE_W}:{SAMPLE_H}", "format=gray"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(recording), "-vf", ",".join(filters),
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    size = SAMPLE_W * SAMPLE_H
    return [normalize(raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)]


def sample_slides(pdf: Path, work: Path) -> list[list[float]]:
    """Return one normalized grayscale sample per page of a PDF."""
    shutil.rmtree(work, ignore_errors=True)  # pages of an earlier, different PDF
    work.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-gray", "-scale-to-x", str(SAMPLE_W), "-scale-to-y", str(SAMPLE_H),
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

def screen_changes(samples: list[list[float]], change: float = CHANGE) -> list[int]:
    """Return the seconds where a new screen appears and then stays still."""
    kept: list[int] = []
    last = None
    for t, sample in enumerate(samples):
        if last is not None and distance(sample, last) <= change:
            continue
        ahead = samples[t + 1:t + 1 + STILL_SECONDS]
        if len(ahead) == STILL_SECONDS and all(distance(sample, s) < STILL for s in ahead):
            kept.append(t)
            last = sample
    return kept


def limit_changes(samples: list[list[float]], per_hour: int) -> list[int]:
    """Return screen changes, raising the change threshold until they fit per_hour."""
    allowed = max(MIN_CAPTURES, math.ceil(per_hour * len(samples) / 3600))
    change = CHANGE
    kept = screen_changes(samples, change)
    while len(kept) > allowed:
        change *= 1.25
        kept = screen_changes(samples, change)
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
        # Build-up slides differ by one bullet: prefer the latest page that ties.
        matches.append(max(i for i, d in enumerate(distances) if d <= best + TIE) + 1)
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
                        "-frames:v", "1", str(out_dir / name)], check=True)
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
    parser.add_argument("--max-captures-per-hour", type=int, default=CAPTURES_PER_HOUR)
    parser.add_argument("--preview", action="store_true", help="save one frame at 1:00 and stop")
    args = parser.parse_args()

    recording = args.recording.resolve()
    out_dir = recording.with_name(recording.name + ".prepared")
    out_dir.mkdir(exist_ok=True)
    if args.preview:
        preview = out_dir / "preview.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "60", "-i", str(recording),
                        "-frames:v", "1", str(preview)], check=True)
        print(preview)
        return 0

    transcript, source = transcribe(recording, out_dir, args.language)
    cues = parse_vtt(transcript.read_text(errors="replace"))

    has_video = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                "stream=index", "-of", "csv=p=0", str(recording)],
                               capture_output=True, text=True, check=True).stdout.strip()
    if not has_video:
        length = int(cues[-1].end) + 1 if cues else 0
        segments = [Segment(0, length)]
    else:
        samples = sample_video(recording, args.crop)
        if args.slides:
            slides = sample_slides(args.slides, out_dir / "slide-samples")
            segments = slide_segments(match_slides(samples, slides))
        else:
            changes = limit_changes(samples, args.max_captures_per_hour)
            frames = save_frames(recording, changes, capture_times(samples, changes), out_dir)
            segments = change_segments(changes, len(samples), frames)

    markdown = write_markdown(recording, cues, segments, source, with_slides=bool(args.slides))
    (out_dir / "recording.md").write_text(markdown)
    print(out_dir / "recording.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
