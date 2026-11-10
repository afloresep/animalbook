# Updating a book

A book grows with its project. An update run changes what is out of date and
adds what is new. It never rewrites the whole book.

## 1. Find what is new

Read `last_build` in `book.json`. Then collect what changed since then:

- `git log --since=<last_build.date>` and `git diff <last_build.commit>..HEAD
  --stat` in the project: new code, new outputs, changed docs.
- Meetings after `last_build.date`, when the project has a meeting source.
- New or changed drafts, handouts and memories.

## 2. Propose changes chapter by chapter

Give the user one short table: chapter, what to change, the source that
prompts it. Changes are of four kinds: a new section, a corrected number or
claim (name the old and new value and the source), a new history entry (in the
appendix or as a dated callout, as `history` says), and a `\todo` that can now be
written. Plan changes to the parts or the look go back through the questions in
[planning.md](planning.md).

Each part keeps its page budget (`parts[].pages` in `book.json`). When the new
material would push a part more than 15% over, the table says so and proposes
what to cut or move to an appendix to make room. Raising a budget is the user's
call: ask, and change `book.json` only when they agree. A book with no
`target_pages` yet gets the length question from [planning.md](planning.md)
once, with its current length as the proposal.

Stop until the user agrees. Apply only what they agreed to.

## 3. Apply, build, record

Apply the agreed changes with the rules in [writing.md](writing.md). Build and
look at the changed pages (SKILL.md, step 5). Then set `last_build` to today's
date and the project's current commit:

```bash
git -C <project> rev-parse --short HEAD
```

## Bring in an existing LaTeX book

A book written before this skill keeps its content. Only its look changes.

1. Copy the whole book folder somewhere safe first, and confirm the copy has
   `book.tex`, the chapter files and the figures.
2. Run the planning interview for the look only (title, author, imprint, cover,
   fonts, callout style, history), and write `book.json` with the existing parts
   marked `written`.
3. Run `setup_book.py` and the cover steps.
4. Replace the preamble of `book.tex`, from `\documentclass` to
   `\begin{document}`, with the one in `<skill>/tex/book-template.tex`. Keep any
   macro of the old book that the style does not provide, and map old callout
   macros onto the style's ones, for example
   `\newcommand{\askmentor}[1]{\questionsfor{my mentor}{#1}}`. Delete old definitions
   of macros the style already has (`\keyidea`, `\careful`, `\workedexample`,
   `\inproject`, `\sources`, `\ev`, `\todo`, `\code`, `\smallnote`), or LaTeX stops
   with "Command already defined".
5. Replace the old title page with the template's front matter (cover,
   half-title, copyright page, contents) and add the colophon and index at the end.
6. Build. Old chapters often hold tables and long paths sized for another page;
   list the overfull boxes and fix them in the chapter files only where the user
   agrees.
