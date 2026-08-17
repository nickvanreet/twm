# Build cotd.js — the Card-of-the-Day story layer the app loads.
#
# Sources (all in tools/enrichment/, English is the record of truth):
#   sv6_lore.json              164 entities: headline + lore_fact
#   sv6_secret_art_notes.json   59 artwork notes for #168-226
#   sv6_card_of_day_enrichment.json  226 cards: entity, tier, context, alternate_of
#   nl/ent_*_nl.json, nl/art_*_nl.json   the Dutch layer (build-time translation)
#
# Everything the base card API already knows (artist, rarity, hp, attacks,
# abilities, images) is deliberately NOT copied here; the app reads that from
# cards.js / RAW. Fields the round-10 spec says never to display verbatim
# (card_of_the_day, display_text, fun_fact, quality, tags, sources) are dropped.
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "enrichment")
NL = os.path.join(SRC, "nl")
OUT = os.path.join(HERE, "..", "cotd.js")


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def load_nl(pattern):
    rows = []
    for p in sorted(glob.glob(os.path.join(NL, pattern))):
        with open(p, encoding="utf-8") as f:
            rows += json.load(f)
    return rows


lore = load("sv6_lore.json")["entities"]
art = load("sv6_secret_art_notes.json")["cards"]
cards = load("sv6_card_of_day_enrichment.json")["cards"]
# the one base-API fact the app does not already ship: who drew the card
artists = load("sv6_artists.json")

nl_ent = {r["entity"]: r for r in load_nl("ent_*_nl.json")}
nl_art = {r["id"]: r for r in load_nl("art_*_nl.json")}
print(f"sources: {len(lore)} entities, {len(art)} artwork notes, {len(cards)} cards")
print(f"dutch:   {len(nl_ent)}/{len(lore)} entities, {len(nl_art)}/{len(art)} artwork")

# ---- entities: Dutch when we have it, English as the documented fallback ----
ents, fell_back = {}, []
for e in lore:
    name = e["entity"]
    d = nl_ent.get(name)
    if not d:
        fell_back.append(name)
    ents[name] = {"h": (d or e)["headline"], "l": (d or e)["lore_fact"]}

# ---- cards: keyed by NUMBER, because the binder has 373 slots and a
# reverse-holo slot must show the story of its base number ----
out_cards = {}
for c in cards:
    alt = c.get("alternate_of")
    n = str(c["number"])
    # collector_context is English prose; the app writes the tier line in Dutch
    out_cards[n] = {
        "e": c["entity"],
        "t": c.get("collector_tier"),
        "a": int(alt.split("-")[1]) if alt else None,
        "ar": artists.get(n),
    }

# ---- artwork notes, keyed by number too ----
out_art = {}
for a in art:
    d = nl_art.get(a["id"])
    src = a["artwork"]
    mood = d["mood"] if d else [m.strip() for m in src["mood"].split(",")]
    out_art[str(a["number"])] = {
        "o": (d or src)["observation"] if d else src["observation"],
        "k": (d["story_hook"] if d else src["story_hook"]),
        "m": mood,
        "s": (d["visual_style"] if d else src["visual_style"]),
    }

payload = {"v": 1, "lang": "nl", "ents": ents, "cards": out_cards, "art": out_art}
body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
js = ("/* Card-of-the-Day story layer: 164 entity stories, 226 card links and 59\n"
      "   artwork notes, translated to Dutch at build time by tools/build_cotd.py.\n"
      "   Card facts (artist, rarity, attacks, HP) come from the app's own data. */\n"
      "const COTD=" + body + ";\n")
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(js)

size = os.path.getsize(OUT) / 1024
print(f"wrote cotd.js: {size:.0f} KB  ({len(ents)} entities, {len(out_cards)} cards, {len(out_art)} artwork)")
if fell_back:
    print(f"WARNING: {len(fell_back)} entities still English: {', '.join(fell_back[:8])}")
missing_art = [a["id"] for a in art if a["id"] not in nl_art]
if missing_art:
    print(f"WARNING: {len(missing_art)} artwork notes still English: {', '.join(missing_art[:8])}")
# every card must resolve to an entity story, or that day would show nothing
orphans = [n for n, c in out_cards.items() if c["e"] not in ents]
if orphans:
    print(f"ERROR: {len(orphans)} cards have no entity story: {orphans[:10]}")
    sys.exit(1)
print("every card resolves to a story")
