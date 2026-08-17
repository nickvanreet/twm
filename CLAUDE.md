# TWM — Twilight Masquerade collectie-app

Single-file PWA that tracks a 12-year-old's Pokémon TCG "Twilight Masquerade" (SV6)
collection. Deployed to GitHub Pages: https://nickvanreet.github.io/twm/ — his phone
is a Samsung Galaxy A15 running Samsung Internet, and that phone is the target, not
the desktop browser.

## Architecture — do not "modernize" it

- One page: `index.html` (~7300 lines: CSS + markup + JS in one file), plus generated
  data (`cards.js`, `decks.js`, `scan.js`, `cotd.js`), `sw.js`, `manifest.webmanifest`,
  `art/`, `icons/`, `fonts/inter-var.woff2`, and `tools/` (Python generators).
- No framework, no bundler, no npm, no build step. Keep it that way.
- All state is localStorage under `twm:*` keys, every key listed in `BK_KEYS` so
  backup/restore keeps working. **IndexedDB was offered and declined — do not build it.**
- A **second set** is planned. Never hard-code `sv6`, `373`, `167` or 12-slots-per-page
  where `SLOTS.length`, `bPer()`, `bTotal()`, `pad3()` exist. Do not build a set
  switcher yet.

## Release ritual (the one thing you must never skip)

Bump **both together, same number**, in every release that touches any shipped file:

- `const APPV="vNN"` in index.html
- `SHELL_CACHE = "twm-shell-vNN"` in sw.js

The SW matches with `ignoreSearch`, so the `?v` query alone does NOT invalidate an
installed phone's copy. After deploy the phone needs a full app close + reopen.
Commit per task (`round N: <what>`), push to `main`, then verify the live version:
Pages serves the new `sw.js` within a minute or two — poll it before telling the user
it is live.

## Dev loop

`.claude/launch.json` (port 8123) lives in this repo. Start
`python -m http.server 8123` in the repo, `preview_start` with name `twm`, drive the
page with `javascript_tool` assertions (seed `twm:collection` etc. in localStorage,
reload, assert). Cache-bust local reloads with `?vNN`. The browser pane blocks the
camera — scanner UI must open and fail gracefully there, which is itself a test.
Local SW debris can serve stale copies: unregister + clear caches when the console
shows errors from code that no longer exists.

## Design system — Nocturne

- Tokens in `:root`: ground `#161826`, surface `#232532`, nav `#1b1d2c`, tint
  `#2b2741`, edges `#3f424d`/`#292b31`, text `#e9e9ed`, muted `#9397ab`/`#75798c`/
  `#b2b6ca`, accent `#b5abfc` (`--n-a4`), accent text `#d2cefd`, ring `#796cbf`.
  Radius 8/14. Self-hosted Inter, weight ≤500, tabular numerals for numbers.
- **Never invent a colour.** The old dusk palette vars resolve to Nocturne; never
  reintroduce gold `#F5B944` (exception: `TYCOL.E`, an energy-type colour, stays).
- Exactly one green/red pair: `.tr.up{#7CD9A5}` / `.tr.down{#F09090}`. The wishlist's
  `.wtr` uses the same two colours with the meanings inverted on purpose.
- No emoji in UI chrome. Icons are Phosphor paths inlined as `<symbol>` sprites.
- Touch targets ≥48dp of **hit area** — visual size may stay smaller; expand with a
  transparent `::after{inset:-Npx}`. Nothing a user must read below 11px.
- Samsung Internet floor: `content-visibility` needs a single-value
  `contain-intrinsic-size` fallback declared first; no `backdrop-filter`;
  transform/opacity-only animation.

## Product rules

- Dutch copy, je-vorm, readable by a ten-year-old. Card names, attack names and
  rarity names stay English (that is what is printed on the card).
- **One undo model:** the session bar (`bSession` + `#bsession`). Never a timed
  toast-undo, never a second undo surface, never a modal on an add path.
- Recognition stays on the device — no camera frames leave the phone.
- Money is honest: `twm:valuehist` snapshots are never fabricated; days priced from
  built-in fallbacks carry `f:1` and are excluded from the delta, sparkline and
  biggest-mover. `eur()` does not handle negatives — use `eur(Math.abs(x))` with an
  explicit `−` (U+2212) or `+`.
- Daily things (card of the day, vraag van de dag) are seeded from the local date via
  `cotdHash` — deterministic, same all day, `>>>` shifts only. `vYest()` walks the
  calendar, not 24h (DST). One attempt per day on the daily question; the streak
  counts days *played*, not days correct.

## Art

Only artwork the user personally supplies may be committed (his assets live in
`C:\Users\nvanreet\Downloads\Twilight_Masquerade_Assets`). Never fetch official or
fan art from the web into the repo. Genuine wrapper scans only for pack faces.
`art/cardback.webp` was supplied by the user. New shipped art goes into the `SHELL`
list in sw.js.

## Process

The user iterates with Claude Design ("App homepage design proposal") and returns
with handoff zips: round files + `PUNCHLIST.md` + `BUILD-NEXT.md`. Rounds 1–14 are
shipped and adversarially reviewed (current release: v66). For each new round: read
only that round's file, build it, run its **Acceptance checks** as real browser
assertions before calling it done, and report what passed. When a spec conflicts
with measured reality, trust the measurement and say so.
