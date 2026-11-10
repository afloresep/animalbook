# Recordings

How to turn a video or audio recording (a class, a talk, a meeting, a demo)
into a source the book can cite. Claude cannot watch a video: it reads the
transcript and, where needed, still images. `prepare_recording.py` makes both,
on this machine. The recording never leaves it; only the text and images you
read do.

Run every command below with `export PATH="$HOME/.animalbook/bin:$PATH" &&` in
front when `check_deps.py` said the environment is not on `PATH`.

## 1. Gather what exists for each recording

Ask the user, per recording or group of them, before installing anything:

- **A transcript export.** Teams and Zoom can export a `.vtt` with timestamps
  and speaker names. Save it next to the recording with the same name
  (`clase-03.mp4` and `clase-03.vtt`) and it is used instead of transcribing,
  which is faster and keeps the names.
- **The slides as a PDF.** Better than anything read off the video: the text,
  formulas and numbers are exact, and a slide shown for two seconds is still
  complete. The video then only says when each slide was on screen.
- **The spoken language**, when it is not obvious (`--language es`).

## 2. Tools

Run `check_deps.py` and look at its two `optional` recording groups.

- **ffmpeg** is always needed. On macOS without Homebrew it comes from
  `setup_env.sh --recordings`.
- **Whisper** (speech to text) is needed only for recordings with no `.vtt`
  export. If every recording has one, skip it. Otherwise offer the two sizes
  and let the user pick; recommend light:
  - `setup_env.sh --whisper light`: whisper.cpp with a compressed copy of the
    Whisper large-v3-turbo model, about 0.6 GB in all. Any Mac. Accurate
    enough for classes and talks.
  - `setup_env.sh --whisper full`: mlx-whisper with the uncompressed model,
    about 3.3 GB, most of it PyTorch. Apple Silicon only. For a user who
    wants the uncompressed model and has the space.

  Both options include ffmpeg. When both Whispers are installed, the script
  uses the full one. On Linux, `check_deps.py` prints how to get whisper.cpp
  and the model.

Stop until the user has run what they chose and `check_deps.py` no longer
lists it.

## 3. Where the output goes

Write each recording's output inside the book folder, which is private (see
SKILL.md, "Always"): `--out <book_dir>/recordings/<recording name>`. Never next
to the recording when that is in a shared or published folder. Record the
recording's role in `book.json` under `recordings` (see
[planning.md](planning.md)).

## 4. Choose the area that shows the slides or screen

A person on camera changes the picture all the time, so screen changes and
slide matches look only at the area that shows the slides or shared screen.
Save one frame and look at it:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --preview --out <out>
```

An audio recording prints `audio only` and needs no crop: go to step 5.
Otherwise read the printed `preview.png`, find the slides or shared screen, and write
its box as `W:H:X:Y` in pixels of that frame (width, height, left, top),
leaving out the camera tiles and the meeting toolbar. With `--slides` the box
must hold the whole slide and nothing else, edge to edge: the slide is compared
with the PDF page as a picture, and a box that cuts or pads it matches badly. When the slides fill the
whole frame, leave `--crop` out. A recording with no screen at all (only people
talking) needs no crop: it gets the transcript alone.

## 5. Prepare it

With the slides:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --out <out> --slides <deck.pdf> --crop W:H:X:Y
```

Without them:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --out <out> --crop W:H:X:Y
```

Transcribing takes a while (minutes per hour of audio): run it in the
background. A transcript from an earlier run is reused; add `--retranscribe`
after changing `--language` or the recording. The result is
`<out>/recording.md`:

- With `--slides`: one section per stretch a slide was on screen, such as
  `## Slide 7, 12:30-15:10`, holding what was said meanwhile. Sections marked
  `no slide on screen` are moments with the camera or something else shown.
- Without them: one section per screen change, pointing to a capture in
  `frames/`. Open a capture only when the words alone do not explain the
  passage (a diagram, code on screen). Do not read them all.

## 6. Check before trusting it

Look at the section list of `recording.md` before writing from it:

- **Slides out of order, or one slide for an hour.** The crop is probably
  wrong. Run `--preview` again and fix the box.
- **Build-up slides** (one bullet more on each page) look almost the same; the
  later page wins a tie, so a few seconds can land on the next page. That is
  harmless for writing.
- **A warning that the transcript has no text.** The recording may have no
  speech, or Whisper failed: try `--retranscribe` with `--language`.
- **Whisper mishears names, technical terms and numbers.** Check them against
  the slides or the user's notes before quoting.

## 7. Use it

Read `recording.md` with the slides open: the slide gives the exact content,
the transcript the explanation, the examples and the questions asked. Cite by
recording and time, as `writing.md` says. Whether what was said may give
numbers and definitions depends on the role the user gave the recordings in
planning (`recordings` in `book.json`: content or context).

A transcript names the people who spoke. Keep the book private, as for
meetings, and ask before naming anyone other than the main speaker (a teacher,
a presenter).
