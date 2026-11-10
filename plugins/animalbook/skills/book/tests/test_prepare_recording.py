"""Tests for turning a recording into a transcript split by slide or screen."""

import shutil
import subprocess
import sys

import prepare_recording as pr
import pytest

SIZE = pr.SAMPLE_W * pr.SAMPLE_H


def flat(value: float, noise: int = 0) -> list[float]:
    """A sample with a fixed pattern, shifted by `noise` in a corner."""
    pixels = bytes(((i * 7) % 256 + value) % 256 for i in range(SIZE))
    pixels = bytes(min(255, p + noise) if i < 800 else p for i, p in enumerate(pixels))
    return pr.normalize(pixels)


def test_parse_vtt_keeps_speakers_and_drops_tags():
    vtt = """WEBVTT

1
00:00:01.000 --> 00:00:03.500
<v Ana López>Hola a todos</v>

00:01:02.000 --> 00:01:04.000
<i>segunda</i> línea
"""
    cues = pr.parse_vtt(vtt)
    assert [(c.start, c.text) for c in cues] == [(1.0, "Ana López: Hola a todos"), (62.0, "segunda línea")]


def test_screen_change_needs_a_still_screen():
    a, b = flat(0), flat(90)
    moving = [flat(0, noise=n * 60) for n in range(4)]  # a corner that never stops changing
    samples = [a] * 5 + [b] * 5 + moving
    assert pr.screen_changes(samples) == [0, 5]



def test_default_limit_keeps_every_slide_of_a_busy_talk():
    # 40 slides in 30 minutes, one every 45 s, as in a typical talk.
    samples = [flat(0 if i % 2 == 0 else 90) for i in range(40) for _ in range(45)]
    assert len(pr.limit_changes(samples, pr.CAPTURES_PER_HOUR)) == 40


def test_capture_is_the_last_still_second_of_its_stretch():
    a, a_built, b = flat(0), flat(0, noise=20), flat(90)  # a_built: one more bullet on a
    fade = flat(45, noise=200)
    b_half = flat(150)  # b animating in: still for 2 s, too short to count as a change
    samples = [a] * 4 + [a_built] * 4 + [b_half] * 2 + [fade] + [b] * 5
    changes = pr.screen_changes(samples)
    assert changes == [0, 11]
    assert pr.capture_times(samples, changes) == [7, 15]

def test_slide_matching_prefers_later_tie_and_folds_flicker():
    slides = [flat(0), flat(0), flat(120)]  # pages 1 and 2 tie, as in a build-up slide
    samples = [flat(0)] * 6 + [flat(120)] * 1 + [flat(0)] * 2 + [flat(120)] * 6
    segments = pr.slide_segments(pr.match_slides(samples, slides))
    assert [(s.slide, s.start, s.end) for s in segments] == [(2, 0, 9), (3, 9, 15)]


def test_markdown_puts_each_cue_under_its_segment():
    cues = [pr.Cue(1, 2, "uno"), pr.Cue(7, 8, "dos")]
    segments = [pr.Segment(0, 5, slide=1), pr.Segment(5, 10, slide=2)]
    text = pr.write_markdown(pr.Path("clase.mp4"), cues, segments, "exported", with_slides=True)
    assert text.index("## Slide 1") < text.index("uno") < text.index("## Slide 2") < text.index("dos")


needs_tools = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("ffmpeg", "ffprobe", "convert", "pdftoppm")),
    reason="needs ffmpeg, ImageMagick and Poppler",
)


@pytest.fixture
def lecture(tmp_path):
    """A 12 s Teams-like video and its .vtt: slides A then B in the top-left 480x270,
    and a moving 'camera' tile beside them, outside the slide area."""
    for name, color, shape in (("a", "navy", "circle 320,180 320,60"), ("b", "darkred", "rectangle 120,80 520,280")):
        subprocess.run(["convert", "-size", "640x360", "xc:white", "-fill", color, "-draw", shape,
                        str(tmp_path / f"{name}.png")], check=True)
    subprocess.run(["convert", str(tmp_path / "a.png"), str(tmp_path / "b.png"), str(tmp_path / "slides.pdf")],
                   check=True)
    video = tmp_path / "clase.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-loop", "1", "-t", "6", "-i", str(tmp_path / "a.png"),
                    "-loop", "1", "-t", "6", "-i", str(tmp_path / "b.png"),
                    "-f", "lavfi", "-t", "12", "-i", "testsrc2=size=128x96:rate=10",
                    "-filter_complex", "[0][1]concat=n=2:v=1:a=0,fps=10,scale=480:270,pad=640:360:0:0:gray[s];"
                    "[s][2]overlay=W-w-4:H-h-4,format=yuv420p",
                    "-c:v", "mpeg4", "-q:v", "3", str(video)], check=True)
    (tmp_path / "clase.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nsobre el círculo\n\n"
        "00:00:08.000 --> 00:00:10.000\nsobre el rectángulo\n")
    return tmp_path, video


def _run(*args):
    subprocess.run([sys.executable, str(pr.Path(pr.__file__)), *map(str, args)], check=True,
                   capture_output=True)


@needs_tools
def test_slides_get_their_time_and_words(lecture):
    tmp_path, video = lecture
    _run(video, "--slides", tmp_path / "slides.pdf", "--crop", "480:270:0:0")
    text = (tmp_path / "clase.mp4.prepared" / "recording.md").read_text()
    assert text.index("## Slide 1, 00:00-00:0") < text.index("círculo")
    assert text.index("círculo") < text.index("## Slide 2, 00:0") < text.index("rectángulo")


@needs_tools
def test_without_slides_each_screen_gets_a_capture(lecture):
    tmp_path, video = lecture
    _run(video, "--crop", "480:270:0:0")
    out = tmp_path / "clase.mp4.prepared"
    assert len(list((out / "frames").glob("*.png"))) == 2
    assert (out / "recording.md").read_text().count("screen `frames/") == 2
