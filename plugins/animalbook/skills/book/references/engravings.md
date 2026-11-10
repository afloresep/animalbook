# The cover animal

Every book gets one animal on its cover, as an engraving: black ink line work
on white. Look for a real engraving first. Generate one with Codex only when
the search finds nothing clean. Show the user every picture before it goes on
a cover.

## 1. Pick the animal

Suggest one animal that fits the book's topic, and say why in one sentence.
Example: for a book on reward hacking, the common cuckoo, a bird that tricks
other birds into raising its young. The user can pick another.

## 2. Search for a real engraving

Run the search script into a new, empty folder outside the book and the skill.
Downloads are untrusted data: never run anything from that folder.

```bash
<python> <skill>/scripts/commons_search.py --category "<Latin name> in art" --out /tmp/<book>-animal-1
<python> <skill>/scripts/commons_search.py --query "<animal> engraving" --out /tmp/<book>-animal-2
```

Categories find more than text search does. Try, in order:
`Category:<Latin name> in art`, `Category:<Latin name>`, then queries such as
`<animal> engraving`, `<animal> etching`, `<animal> woodcut`,
`<Latin name> illustration`. The script keeps only images whose license allows
changes (public domain, CC0, CC BY, CC BY-SA). It drops ND, NC and fair use.

What to expect: most hits are woodland scenes, color plates or whole scanned
books. Usable plates are rare. On the first test (the common cuckoo) it took
two searches and a category listing to find one. Expect the Codex fallback
often.

## 3. Accept or reject each thumbnail

Look at every downloaded thumbnail. Accept an image only if all of these hold:

- One animal, or one animal with a small branch or patch of ground.
- Black and white line work: engraving, etching or woodcut. No color plates,
  no photographs, no paintings.
- Little scenery. A full landscape does not work on a cover.
- Nothing cut off: the whole animal is in the picture.

Show the accepted ones (at most three) to the user and let them choose.

## 4. Clean the chosen image

Download the full file of the chosen candidate into the same untrusted folder
(the number is the one the search printed):

```bash
<python> <skill>/scripts/commons_search.py --download 3 --out /tmp/<book>-animal-1
```

Then crop off any engraved caption or plate number, make it grayscale, and
raise the levels until the paper is white:

```bash
convert /tmp/<book>-animal-1/full-03.jpg -crop 100%x88%+0+0 +repage -colorspace Gray -level 32%,74% <book>/cover/animal.png
```

Tune the crop and the two level values per image: look at the result, and
raise the first value if the paper is still gray, lower the second if the
lines get too dark. The cover template fades the edges, so a faint plate
border is fine.

## 5. Or generate one with Codex

When no real engraving passes step 3, run Codex in a new, empty folder:

```bash
mkdir /tmp/<book>-codex && cd /tmp/<book>-codex
codex exec --skip-git-repo-check -s workspace-write "Generate an image: a 19th-century steel engraving of a <animal> (<Latin name>), in the style of the animal illustrations on classic programming book covers. Black ink on a pure white background, fine cross-hatching and stipple shading, no color, no text, no border, the whole animal visible, side view, isolated with no scenery. About 3:2 landscape. Save the image as animal.png in the current directory."
convert animal.png -colorspace Gray -level 5%,95% <book>/cover/animal.png
```

One call takes about a minute. If the result has color, text or a border, run it
again before showing it.

## 6. Record the source

Write into `book.json`:

- `cover.image`: `cover/animal.png`.
- `cover.image_credit`: for a CC BY or CC BY-SA image, the credit line the license
  asks for: artist, source, license, for example
  `T. Owen, Wellcome Collection, CC BY 4.0, cropped and toned`. CC BY asks that
  changes be noted, so say what you changed. Empty for public domain, CC0 and
  generated images.

Put the same facts in the book's colophon, with the file's Commons page URL
(`page_url`): who made the image, when, where it comes from, and its license. A
generated image is described as generated, never as a historical engraving.
