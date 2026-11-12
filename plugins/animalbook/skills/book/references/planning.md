# Planning a book

Spend one short interview here instead of a rewrite later. Before asking, look
at the obvious sources (the repository layout, `README`, `CLAUDE.md`, recent
git history, any existing drafts) so every question comes with a proposed
answer. Facts you can look up are your job, not questions.

## How to ask

The user should answer by picking, not by reading and writing paragraphs.

- Ask with the multiple-choice question tool when the harness has one
  (`AskUserQuestion` in Claude Code). It takes up to 4 questions per call;
  each question gets 2 to 4 options, and the user can always type their own.
  Without such a tool, ask the same questions as a short numbered list with
  lettered options.
- The question dialog hides the text you wrote before it, so anything the
  user needs to answer goes in the question or its options, not before them.
- Each option is a short label (2 to 5 words) and one line of description.
  Put your proposed answer first and add "(Recommended)" to its label.
- Before the first question, say in one or two lines what you found in the
  sources. Do not explain the plan before asking.
- Do not ask about what has a good default. Fonts, the imprint, the ribbon and
  the author name are proposed in the plan summary, where the user can change
  them.

## Round 1: what the book is

1. **Reader.** Who reads the book and what they already know. Options are
   2 or 3 likely readers you inferred, for example "Me, later", "A new team
   member", "My supervisor". This sets how much background Part I needs.
2. **Purpose.** What the reader should be able to do after reading it. Options
   are 2 or 3 concrete goals, for example "Explain the project to others" or
   "Pass interviews on these topics".
3. **Length.** How many pages the main chapters take, front matter,
   appendices and index not counted. Always these three options, the one that
   fits the purpose first:
   - **Short, about 40 pages**: a briefing read in an evening, for catching up
     or handing over.
   - **Medium, about 80 pages**: the project with its methods and main
     results, for a new team member or a supervisor.
   - **Long, about 150 pages**: a reference that covers the code and every
     result in detail, for someone who will work on the project.

   Recommend short or medium unless the purpose needs a reference. A shorter
   book that gets read beats a complete one that does not. A typed number is
   the target.
4. **History or recordings**, only when the sources have them:
   - Meeting notes or another dated record: where the history of decisions
     goes. `Appendix` (a dated timeline at the back), `Callouts` (short dated
     notes in the topic chapters, such as "Decided on 19 Oct: ..."), `Both` or
     `None`.
   - Video or audio recordings: are they `Content` (classes or talks the book
     teaches from, so what was said can give definitions and numbers) or
     `Context` (meetings that explain decisions)? Recommend content for
     classes and talks, context for meetings. When both kinds exist, ask per
     group.

## Round 2: the look

The user cannot judge a layout from its name, so show it first. Open the two
sample sheets in the skill folder, `<skill>/assets/look/covers.png` (the
three cover layouts) and `<skill>/assets/look/callouts.png` (the three callout
styles): `open <file>` on macOS, `xdg-open <file>` on Linux. When neither
works, give the user the two paths. Say in one line that they are open, then
ask in one call:

1. **Animal.** 3 animals that fit the topic, each with a one-line reason.
2. **Cover.** `Classic`, `Modern` or `Block`, as in `covers.png`. One line
   each: classic has the title in a colored band with the animal below,
   modern a large title on white with the animal in the lower half, block the
   animal on top and the title in a color block at the bottom.
3. **Callouts.** `Tinted`, `Icon` or `Strip`, as in `callouts.png`. One line
   each: tinted is a colored bar and a light tint, icon an engraving in a
   colored disc with no box, strip a colored header strip over a box.

The author is printed on the cover. When the git `user.name` looks like a
handle (one word, such as `jdoe42`), ask a fourth question, **Author**: a full
name found in the sources (git log, README, a paper) as the proposed answer
when there is one, and the handle as the other option; the user can type
their name.

Do not ask for the cover color. Propose one that suits the topic with the
other defaults under the plan; the user sees it on the real cover in step 3
and can change it there.

## The plan

Draft the parts and chapters from the answers: each chapter gets a page
budget, the budgets add up to the length, the most important topics get the
most pages, no chapter gets fewer than 3 (fold it into a neighbor), and
chapters follow topics, not dates. A common shape is foundations (the concepts
and tools), the problem, what was done and found, how the code is built, open
questions, then appendices.

Write the plan as a plain-text outline, columns lined up with spaces, at most
60 characters wide, with the defaults you chose under it:

```
I.  Foundations                              14
    1. The data                               6
    2. The baseline model                     8
II. Results                                  10
    3. What worked                           10
A.  Decision timeline                     extra
                                  Total      24

Cover: deep teal #2f5d62, block, tinted callouts
Fonts: EB Garamond, IBM Plex Sans Condensed
Imprint: PROJECT NOTES · Ribbon: none · Author: A. Author
```

Keep what each chapter covers to yourself until the user asks; `book.json`
gets only the titles.

Then ask one question to confirm: `Looks good (Recommended)`, `Shorter` or
`Change chapters`. The question dialog hides the text you wrote before it, so
the outline goes inside the question: in Claude Code, as the `preview` of
every option (the preview shows the focused option's text in a monospace
box). Without a question tool, print the outline in a code block and ask the
user to reply. On a change, redraw the outline and ask again.

Other supported fonts, when the user asks: serif `Cormorant Garamond` or
`Libre Caslon Display`, sans `Fira Sans Condensed`.

## book.json

Write the answers to `<book_dir>/book.json`. Every key below is required except
where it says otherwise; `setup_book.py` stops with the key name when one is
missing or not supported.

```json
{
  "title": "The Sample Book",
  "subtitle": "Everything a reader needs to follow the project",
  "author": "A. Author",
  "imprint": "SAMPLE NOTES",
  "serif": "EB Garamond",
  "sans": "IBM Plex Sans Condensed",
  "callouts": "tinted",
  "cover": {
    "layout": "classic",
    "color": "#5b3a7a",
    "tagline": "One line printed at the top of a classic cover",
    "ribbon": "Working draft",
    "image": "cover/animal.png",
    "image_credit": ""
  },
  "history": "appendix",
  "target_pages": 80,
  "parts": [
    {"title": "Foundations", "status": "planned", "pages": 20,
     "chapters": [
       {"title": "Probes and Steering", "pages": 8},
       {"title": "Sparse Autoencoders", "pages": 12}
     ]}
  ],
  "last_build": null,
  "recordings": [
    {"path": "lectures/", "role": "content"},
    {"path": "meetings/", "role": "context"}
  ]
}
```

- `subtitle`, `imprint`, `cover.tagline`, `cover.ribbon` and `cover.image_credit`
  may be empty strings. A ribbon with a line break (`"Working draft\nFall 2026"`)
  prints on two lines.
- `recordings` is optional; leave it out when the book uses none. Each `path`
  is a recording or a folder of them, relative to the project; `role` is
  `content` or `context`.
- `target_pages` is the length from round 1. `parts[].chapters` lists each
  part's chapters in book order with their budgets, and `parts[].pages` is
  their sum. All three are optional; a book without them has no length check.
- `parts[].status` is `planned` or `written`. Keep the list in book order.
- `last_build` is `null` until the first build, then
  `{"date": "YYYY-MM-DD", "commit": "<project git commit>"}`.
