# animalbook

A Claude Code skill that writes a book about your project in the style of the
classic engraved-animal programming books. It plans the book with you, writes it
one part at a time from the project's own sources (code, outputs, meeting notes,
drafts, papers), keeps it up to date as the project moves, and lays it out with
an engraved animal on the cover.

<p>
  <img src="docs/images/cover.png" width="300" alt="A sample cover: red title on white, an engraved cuckoo below">
  <img src="docs/images/page.png" width="300" alt="A sample chapter opener with a gray sources box and colored callouts">
</p>

The books are for learning and for keeping up with your own work. They are not
affiliated with any publisher, and no publisher's name or logo appears in them.

## What you get

- A cover in one of three layouts (`classic`, `modern`, `block`) with an animal
  picture: a real public-domain or openly licensed engraving from Wikimedia
  Commons when one fits, or one generated with Codex.
- 7 × 9.19 inch two-sided pages, serif text and condensed sans headings,
  right-aligned chapter openers, numbered figures, tables and code examples.
- Colored callouts in three styles (`tinted`, `icon`, `strip`): key idea,
  careful, worked example, questions, still to write. Gray sidebars for sources
  and "in our project" notes.
- Content rules that keep the book honest: every chapter says where its content
  comes from, numbers come only from files, results carry evidence tags.
- Updates: later runs find what changed since the last build and propose edits
  chapter by chapter.
- Recordings as sources: a class, talk or meeting on video becomes a transcript
  split by slide (with the slide PDF) or by screen change, with timestamps, so
  the book can cite what was said and when. Transcription runs on your machine
  with Whisper, or uses the Teams or Zoom `.vtt` export when there is one.

## Install

In Claude Code:

```
/plugin marketplace add afloresep/animalbook
/plugin install animalbook@animalbook
```

Then, in a project, ask for it: "make a book for this project", "update the
book" or "make a cover for the book".

## What it needs

On its first run on a machine the skill checks for everything below and shows
you the few commands that install what is missing, in order. It never installs
anything itself.

- LuaLaTeX with the packages of the book style. On macOS, `setup_env.sh`
  (below) installs TinyTeX with exactly these, a few hundred MB; you do not
  need MacTeX. On Debian or Ubuntu: `sudo apt install texlive-luatex
  texlive-latex-extra texlive-pictures`.
- Poppler (`pdftoppm`, `pdfinfo`) and ImageMagick (`convert`).
- Chromium or Google Chrome, to draw the cover.
- Python 3.9 or newer, the one macOS ships. The scripts use the standard
  library only.
- Optional: Codex CLI, only for generated cover animals.
- Optional, only for recordings: ffmpeg, and a speech-to-text tool for
  recordings that come without a `.vtt` transcript. It comes in two sizes:
  `light` is whisper.cpp with a compressed Whisper model (about 0.6 GB, any
  Mac); `full` is mlx-whisper with the full model (about 3.3 GB, most of it
  PyTorch, Apple Silicon only).

### On macOS

One script installs what is missing into `~/.animalbook`, with no admin rights
and no Homebrew needed: TinyTeX, and Poppler and ImageMagick when Homebrew did
not provide them. It adds `~/.animalbook/bin` to `PATH` in `~/.zshrc` and is
safe to run again. The skill prints the command with the script's full path
inside the installed plugin. From a clone of this repository it is:

```
bash plugins/animalbook/skills/book/scripts/setup_env.sh
```

For recordings, add one option: `--recordings` (ffmpeg only, when every
recording has a `.vtt`), `--whisper light` or `--whisper full`.

To remove everything it installed:

```
bash plugins/animalbook/skills/book/scripts/remove_env.sh
```

## How a book is laid out

A book lives in a folder inside your project, for example `docs/book/`:

```
docs/book/
├── book.json      the book's settings: title, look, parts, last build
├── book.tex       the main file
├── chapters/      one .tex file per chapter
├── figures/
├── cover/         the animal picture and the rendered cover
└── style/         the book's own copy of the style, fonts and icons
```

Each book keeps its own copy of the style, so it still builds the same way after
the skill changes.

## Tests

```
cd plugins/animalbook
python3 -m pip install --user pytest   # once
python3 -m pytest skills/book/tests -q
```

The build tests need LuaLaTeX and the fonts above.

## Licenses

The code, templates and icons are under the MIT License (`LICENSE`). The fonts in `plugins/animalbook/skills/book/assets/fonts/` are under the SIL Open
Font License; each family's license file sits next to it. The callout icons
were generated with Codex for this project. Cover pictures found on Commons
keep their own licenses, and the skill prints the credit line a license asks for.
