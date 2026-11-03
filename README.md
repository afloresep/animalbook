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

## Install

In Claude Code:

```
/plugin marketplace add afloresep/animalbook
/plugin install animalbook@animalbook
```

Then, in a project, ask for it: "make a book for this project", "update the
book" or "make a cover for the book".

## What it needs

On its first run on a machine the skill checks for everything below and tells you
the install command for anything missing. It never installs anything itself.

- LuaLaTeX with `fontspec`, `luaotfload`, `titlesec`, `tcolorbox`, `enumitem`,
  `imakeidx`, `pdfpages`, `listings`, `fancyhdr`, `caption` and TikZ. On
  Debian or Ubuntu: `sudo apt install texlive-luatex texlive-latex-extra
  texlive-pictures`.
- Poppler (`pdftoppm`, `pdfinfo`) and ImageMagick (`convert`).
- Chromium or Google Chrome, to draw the cover.
- Codex CLI, only for generated cover animals.
- Python 3. The scripts use the standard library only.

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
python3 -m pytest skills/book/tests -q
```

The build tests need LuaLaTeX and the fonts above.

## Licenses

The fonts in `plugins/animalbook/skills/book/assets/fonts/` are under the SIL Open
Font License; each family's license file sits next to it. The callout icons
were generated with Codex for this project. Cover pictures found on Commons
keep their own licenses, and the skill prints the credit line a license asks for.
