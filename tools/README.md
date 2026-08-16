# tools — the generators behind the data files

These scripts produce the generated files the app ships. They are not needed to
run the app; they are needed to *rebuild* its data, and one of them (the scanner)
has to be bit-exact or the camera silently gets worse instead of failing loudly.

Run them with Python 3 and Pillow + numpy:

```bash
pip install pillow numpy
```

## The camera scanner

| step | script | writes |
| --- | --- | --- |
| 1. download every reference scan | `scan_fetch.py` | `scan_imgs/{en,fr,ja}/*` (~47 MB, not in git) |
| 2. build descriptors + measure accuracy | `scan_build2.py` | prints top-1/top-5 under a simulated-photo benchmark |
| 3. emit the file the app loads | `scan_emit2.py [wart]` | `../scan.js` |

`scan_fetch.py` reads the `JPX` map straight out of `index.html`, so the Japanese
scans it downloads always match what the app believes.

**The descriptor format is a contract with `index.html`.** The app re-implements
the same maths in JavaScript (`scanResampleRect`, `scanDescRect`, `scanDualDesc`)
and both sides must agree exactly:

- resample with a fractional box average, not a bilinear resize
- grey = 0.299 R + 0.587 G + 0.114 B
- 16×16 dHash horizontally, then 16×16 vertically → 512 bits, packed MSB first
- a 6×6 mean-subtracted RGB grid, stored as int8
- twice: once over the whole card, once over the art window
  `[0.055, 0.105, 0.945, 0.465]` (fractions of the card, the same window on EN,
  FR and JP layouts)
- `SCANDESC.v` must match the version the app checks (`ensureScanDB`)

If you change any of that, change both sides in the same commit and bump `APPV`
in `index.html` **and** `SHELL_CACHE` in `sw.js`, or installed phones keep the
old `scan.js` (the service worker matches with `ignoreSearch`, so the `?v` query
will not save you).

Regression test before shipping a rebuild: regenerate the current set and diff
the new `scan.js` against the committed one. It should be byte-identical.

## Card data

- `build_cards.py` — turns a raw API dump of the set into `../cards.js`
  (the deck builder's card facts: attacks, costs, abilities, evolution lines).
- `validate_decks.py` — checks the hand-written decks in `deck_raw_nl.json`
  against those facts (60 cards, ≤4 per name, ≤1 ACE SPEC, evolution support,
  energy types that the attacks actually ask for) and only then writes
  `../decks.js`. It refuses to emit an illegal deck on purpose.

`deck_raw_nl.json` holds the Flemish deck texts and is the one input here that
was written by hand and fact-checked; keep it with the repo if you ever revive
this pipeline.

## Adding a second set

Everything above is per-set. The scanner descriptors, the card facts and the
deck data would all need a second run — but the app's storage keys collect
cards by bare card number (`"141"`), so two sets cannot share one install
without a data migration. See the notes in the commit history before starting.
