---
name: book
description: "Use when the user wants a book for a project: plan, write, update or rebuild a project book in the style of the classic engraved-animal programming books, from the project's own sources (code, outputs, meetings, memories, drafts, literature). Triggers: make a book for this project, update the book, rebuild the book, book cover, new chapter. Not for a single short report on one piece of work, or for README and reference docs."
---

# Project book

This skill makes a book about one project, in the style of the classic
engraved-animal programming books: an animal on the cover, 7 x 9.19 inch pages,
serif text with condensed sans headings, and colored callouts that say what to
remember and what to be careful about. The book is written from the project's own
sources and grows with it.

`<skill>` below means the folder this file is in. The scripts are stdlib
Python and need Python 3.10 or newer. `<python>` below means
`~/.animalbook/conda/bin/python3` when that file exists (the environment's
Python; the system `python3` of macOS is 3.9 and cannot run them), and
`python3` otherwise. A book lives in its own folder inside the project
(for example `docs/book/`), holding `book.tex`, `book.json`, `chapters/`,
`figures/`, `cover/` and `style/`.

The work goes in this order. Each step says when to stop for the user.

## 0. First run on a machine: dependencies

```bash
<python> <skill>/scripts/check_deps.py
```

If it prints `missing` lines (exit code 1), show the user each one with its
install command and stop until they say it is done. Lines marked `optional`
(Codex, used only for generated cover animals, and the tools for recordings) do
not stop the run: mention them and go on. Never install anything yourself and
never fall back to a simpler layout.

### Without Homebrew or admin rights (macOS on Apple Silicon)

On macOS with Homebrew the install commands are Homebrew's. Without it, every
missing item points instead to one script, which the user runs, that installs
everything into `~/.animalbook` with no admin rights: TinyTeX with the
template's LaTeX packages, and Python, Poppler, ImageMagick and pytest from
conda-forge through micromamba. It downloads about 70 MB for TinyTeX plus the conda packages,
and adds one line to `~/.zshrc` that puts `~/.animalbook/bin` on `PATH`.

```bash
bash <skill>/scripts/setup_env.sh
```

It takes a few minutes, is safe to run again (for example after a failed
download) and ends by running `check_deps.py`. Recordings need two more tools,
ffmpeg and mlx-whisper with its speech model (about 3.3 GB more; the base
environment is about 850 MB): `check_deps.py` lists them as optional, and
`setup_env.sh --video` installs them.

When `check_deps.py` says Python is too old, run it again with the
environment's Python. When it says the environment is installed but not on `PATH` (a
shell started before the setup), start every command of this skill that calls
`lualatex`, `pdftoppm`, `pdfinfo`, `convert` or `pytest` with
`export PATH="$HOME/.animalbook/bin:$PATH" &&`.

### Removing the environment

When the user asks how to remove it, give them this command:

```bash
bash <skill>/scripts/remove_env.sh
```

This deletes `~/.animalbook` (the video tools and the speech model too) and its
line in `~/.zshrc`. Books already written
stay where they are, but they cannot be built again until the environment is set
up again.

## 1. Plan a new book

Follow [references/planning.md](references/planning.md): one round of
questions, each with your proposed answer, covering the reader, what the book
should let them do, the parts and chapters, where meeting history goes, and the
look. Write the answers to `book.json` and show the user the plan as a short
table of parts and chapters. Stop until they agree.

An existing book in another layout (a LaTeX book written before this skill) is
brought in with the same interview; see "Bring in an existing LaTeX book" in
[references/updating.md](references/updating.md).

## 2. Set up the book folder

```bash
<python> <skill>/scripts/setup_book.py <book_dir>
```

This copies the style, fonts and icons into `<book_dir>/style/` and writes
`style/options.tex` from `book.json`. Run it again after any change to
`book.json`; it never touches `book.tex`, chapters or `book.json`. A new book
starts from `<skill>/tex/book-template.tex`, copied to `<book_dir>/book.tex`.

## 3. The cover

Pick and clean the animal picture with
[references/engravings.md](references/engravings.md): a real engraving from
Wikimedia Commons first, a Codex engraving when nothing clean is found. Show the
user the picture and stop until they accept it. Then:

```bash
<python> <skill>/scripts/render_cover.py <book_dir>
```

Look at `cover/cover.png`: the title fits, nothing overlaps, the fonts are the
book's. Show it to the user.

## 4. Gather sources

Follow [references/writing.md](references/writing.md), section "Sources". Ask
which sources exist, read them, and for the part you are about to write list
the sources per chapter. Do not write before this list exists.

Video or audio recordings (classes, talks, meetings, demos) are read through a
transcript split by slide or screen: follow
[references/recordings.md](references/recordings.md).

## 5. Write one part, build it, stop

Write one part at a time, never the whole book in one go. The rules for every
sentence, number and citation are in [references/writing.md](references/writing.md).
Then build:

```bash
cd <book_dir>
lualatex -interaction=nonstopmode book.tex   # three times: contents, references, index
```

The build passes when `book.log` has no line starting with `!`,
`Overfull \hbox`, `Overfull \vbox` or `Missing character` (a character the font
lacks, which silently disappears from the PDF). Render the part's pages and look
at them:

```bash
mkdir -p /tmp/<book>-pages
pdftoppm -r 70 -png -f <first> -l <last> book.pdf /tmp/<book>-pages/p
```

Fix what looks wrong (a table too wide, a callout split badly, a long path
running into the margin). Then mark the part `written` in `book.json`, show the
user a few page images, and stop for their check before the next part.

## 6. Update an existing book

Follow [references/updating.md](references/updating.md): find what is new since
`last_build` in `book.json`, propose the changes chapter by chapter, apply them
after the user agrees, rebuild, and record the new `last_build`.

## 7. Hand over

Tell the user: the PDF path and page count, what changed in this run, any number
you could not trace to a source file, and what you left out and why. Keep it to a
few lines.

## Always

- Never commit, push or publish. Never edit a file outside the book folder
  without asking.
- A book that is not under git (for example a gitignored folder) cannot be
  restored. Copy the folder before the first change in a run.
- `book.json` holds the user's choices. Change a value there only when the user
  asks.
- A book that quotes meetings is private. Say so on its copyright page and keep
  it in a folder the project does not publish.
