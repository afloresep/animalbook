# Writing the book

The goal is that the reader understands the project, not only its results. A
reader who knows the field but not this project should be able to explain every
method and every decision after reading the chapter that covers it.

## Sources

Ask the user which of these exist, then read them. Do not assume any of them.

- **Meetings.** Notes or transcripts through a meeting MCP server when the
  session has one (Granola or another), or a folder of exported transcripts the
  user names. The project's `CLAUDE.md` may name the server and folder.
- **Recordings.** Video or audio of classes, talks, meetings or demos, read
  through `recording.md` from `prepare_recording.py` (see
  [recordings.md](recordings.md)), never by guessing from the file name.
- **The project's memory.** Claude memories for the project, `CLAUDE.md` and
  its rules. When they name writing, language or privacy rules, follow them;
  they come before the defaults here.
- **Drafts.** Existing handouts, reports, notes, an older version of the book.
- **The repository.** `README`, `docs/`, the code, saved outputs, git history.
- **Literature.** A folder of papers or a notes vault the user points to. Read
  only: cite it, never edit it.

Before writing a part, list for each chapter the files it draws on. A chapter
with no sources yet gets a `\todo` box instead of invented content.

## Rules for content

- **Every chapter opens with `\sources{...}`**, saying where its content comes
  from: paths for code and outputs, documents by name, meetings only as "the
  discussion on <date>", recordings by name and time ("recording 2026-11-03,
  42:15").
- **Numbers come only from files**: an output, a log, committed code, or a
  document that cites one. Meetings give context, the reasons for decisions and
  the questions people asked. They never give a number. Recordings follow the
  role the user gave them in planning: as context they are meetings; as
  content (a class, a talk) what was said and shown can give definitions,
  formulas and numbers, cited by recording and time. A number that was only
  heard, not shown on a slide, is marked as spoken ("said at 42:15"), because
  Whisper mishears numbers as easily as names. Keep a list of
  claim -> source path while writing.
- **Papers** are cited with their arXiv number or address and a section or page.
- **Results carry an evidence tag**: `\ev{finding}` says something about the
  question the project studies; `\ev{method check}` shows a tool works;
  `\ev{negative}` means the tested effect was not shown (say whether the test
  could have shown it); `\ev{lead}` is a pattern that still needs an independent
  test. Report every result, including negative and small ones.
- **Calibrate every claim.** One case is a case, not an effect. A model's label
  is a model judgment, not a human check. A correlation is not a cause. Say how
  many cases a claim rests on.
- **Unwritten sections** get `\todo{P1}{...}` (needed now), `\todo{P2}{...}`
  (useful soon) or `\todo{P3}{...}` (for completeness).
- **History** goes where `book.json` says (`history`): a dated appendix, dated
  callouts in the topic chapters, both, or nowhere. Never chapters by date.

## Rules for prose

- Short sentences, plain words, active voice. Define a term before its first use.
- No em dashes and no filler ("it is worth noting", "importantly").
- A table when more than three numbers are compared. A figure only when it shows
  what a table cannot. Reuse existing figure files; do not run experiments for a
  figure.
- The project's own writing and language rules come first.

## The macros

The style provides these. Use them instead of writing boxes by hand.

| Macro | Use |
|---|---|
| `\sources{text}` | Gray sidebar at the start of each chapter: where its content comes from |
| `\keyidea{text}` | What to remember from a section |
| `\careful{text}` | Concepts that are easy to confuse, common mistakes |
| `\workedexample{title}{text}` | A number from the project computed step by step; numbered per chapter |
| `\inproject{text}` | Gray sidebar: where the concept lives in the repository and outputs |
| `\questionsfor{who}{text}` | Open questions worth raising with someone |
| `\todo{P1}{text}` | A section still to write, with its priority |
| `\ev{finding}` | Evidence tag after a result |
| `\code{path/to/file\_name.py}` | Inline code and paths; write underscores as `\_` |
| `\smallnote{text}` | A small note under a table or figure |
| `codeexample` environment | `\begin{codeexample}{title}` ... `\end{codeexample}`: a numbered code listing, "Example 3-1." |
| `\index{term}` | Index entry |

Figures and tables use the normal `figure` and `table` environments with
`\caption`; they are numbered "Figure 3-2." and "Table 3-1.". Keep callouts short:
three or four lines. Long material belongs in the text.

## The colophon

The last page describes the cover animal, as the classic books do: what the
animal is, one or two facts about it, why it fits this book, and where the cover
picture comes from (artist, date, source, license, or "generated with Codex").

## Before handing over a part

1. **Trace numbers.** Walk the claim -> source list. Open each source and confirm
   the value. List any number you could not confirm.
2. **Overclaims.** Reread each chapter's opening and every `\keyidea` against the
   results below it. None may be stronger than the evidence.
3. **Build and look** (SKILL.md, step 5).
