# Recordings

How to turn a video or audio recording (a class, a talk, a meeting, a demo)
into a source the book can cite. Claude cannot watch a video: it reads the
transcript and, where needed, still images. `prepare_recording.py` makes both,
on this machine. The recording never leaves it; only the text and images you
read do.

Needs `ffmpeg`, and a speech-to-text tool unless every recording comes with a
`.vtt` export: `setup_env.sh --whisper light` (whisper.cpp, about 0.6 GB) or
`--whisper full` (mlx-whisper, about 3.3 GB, Apple Silicon); when both are
installed the script uses the full one. Run every command below with `export PATH="$HOME/.animalbook/bin:$PATH" &&` in front when they
are not on `PATH` yet.

## 1. Gather what exists for each recording

Ask the user, per recording or group of them:

- **A transcript export.** Teams and Zoom can export a `.vtt` with timestamps
  and speaker names. Save it next to the recording with the same name
  (`clase-03.mp4` and `clase-03.vtt`) and it is used instead of transcribing,
  which is faster and keeps the names.
- **The slides as a PDF.** Better than anything read off the video: the text,
  formulas and numbers are exact, and a slide shown for two seconds is still
  complete. The video then only says when each slide was on screen.
- **The spoken language**, when it is not obvious (`--language es`).

## 2. Choose the area that shows the slides or screen

A person on camera changes the picture all the time, so screen changes and
slide matches look only at the area that shows the slides or shared screen.
Save one frame and look at it:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --preview
```

Read the printed `preview.png`, find the slides or shared screen, and write
its box as `W:H:X:Y` in pixels of that frame (width, height, left, top),
leaving out the camera tiles and the meeting toolbar. With `--slides` the box
must hold the whole slide and nothing else, edge to edge: the slide is compared
with the PDF page as a picture, and a box that cuts or pads it matches badly. When the slides fill the
whole frame, leave `--crop` out. A recording with no screen at all (only people
talking) needs no crop: it gets the transcript alone.

## 3. Prepare it

With the slides:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --slides <deck.pdf> --crop W:H:X:Y
```

Without them:

```bash
python3 <skill>/scripts/prepare_recording.py <recording> --crop W:H:X:Y
```

Transcribing takes a while (minutes per hour of audio): run it in the
background. The result is `<recording>.prepared/recording.md`:

- With `--slides`: one section per stretch a slide was on screen, such as
  `## Slide 7, 12:30-15:10`, holding what was said meanwhile. Sections marked
  `no slide on screen` are moments with the camera or something else shown.
- Without them: one section per screen change, pointing to a capture in
  `frames/`. Open a capture only when the words alone do not explain the
  passage (a diagram, code on screen). Do not read them all.

## 4. Check before trusting it

Look at the section list of `recording.md` before writing from it:

- **Slides out of order, or one slide for an hour.** The crop is probably
  wrong. Run `--preview` again and fix the box.
- **Build-up slides** (one bullet more on each page) look almost the same; the
  later page wins a tie, so a few seconds can land on the next page. That is
  harmless for writing.
- **Whisper mishears names, technical terms and numbers.** Check them against
  the slides or the user's notes before quoting.

## 5. Use it

Read `recording.md` with the slides open: the slide gives the exact content,
the transcript the explanation, the examples and the questions asked. Cite by
recording and time, as `writing.md` says. Whether what was said may give
numbers and definitions depends on the role the user gave the recordings in
planning (content or context).

A transcript names the people who spoke. Keep the book private, as for
meetings, and ask before naming anyone other than the main speaker (a teacher,
a presenter).
