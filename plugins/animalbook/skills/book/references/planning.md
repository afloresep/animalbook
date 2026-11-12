# Planning a book

Spend one round of questions here instead of a rewrite later. Before asking,
look at the obvious sources (the repository layout, `README`, `CLAUDE.md`,
recent git history, any existing drafts) so every question comes with a
proposed answer the user can accept or correct.

## The questions

Ask them in one message, numbered, each with your proposed answer.

1. **Reader.** Who reads the book and what they already know. This sets how
   much background Part I needs.
2. **Purpose.** What the book should let the reader do after reading it, for
   example "keep up with the project and explain it to a supervisor".
3. **Parts and chapters.** A table: part titles, chapter titles, one line per
   chapter on what it covers. Organize by topic, not by date. A common shape is
   foundations (the concepts and tools), the problem, what was done and found,
   how the code is built, open questions, then appendices.
4. **History.** Only when meeting notes or a similar dated record exist: where
   the history of decisions goes. `appendix` (a dated timeline of decisions at
   the back), `callouts` (short dated notes inside the topic chapters, such as
   "Decided on 19 Oct: ..."), `both` or `none`.
5. **Recordings.** Only when there are video or audio recordings: for each
   group of them, are they content (a class or talk the book teaches from, so
   what was said can give definitions and numbers) or context (meetings that
   explain decisions)? Propose content for classes and talks, context for
   meetings. Record the answer in `book.json` under `recordings`.
6. **Look.**
   - Cover layout: `classic` (title in a colored band, animal below), `modern`
     (large sans title on white, animal in the lower half) or `block` (animal on
     top, title in a solid color block). Propose a cover color as `#rrggbb`.
   - Fonts: serif `EB Garamond` (default), `Cormorant Garamond` or
     `Libre Caslon Display`; sans `IBM Plex Sans Condensed` (default) or
     `Fira Sans Condensed`.
   - Callout style: `tinted` (colored bar and tint), `icon` (icon in a colored
     disc, no box) or `strip` (colored header strip).
   - The animal (suggest one that fits the topic, with a one-line reason).
   - Imprint: a short name printed where a publisher logo would go, for example
     `<PROJECT> NOTES`.
   - Ribbon: corner ribbon text such as `Working draft`, or none.
7. **Author.** The name on the cover. Propose the git `user.name`.

Wait for the answers. Ask a second round only if an answer opens a real
ambiguity. Facts you can look up are your job, not questions.

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
  "parts": [
    {"title": "Foundations", "status": "planned"}
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
- `parts[].status` is `planned` or `written`. Keep the list in book order.
- `last_build` is `null` until the first build, then
  `{"date": "YYYY-MM-DD", "commit": "<project git commit>"}`.
