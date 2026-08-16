# Compact deck-building dataset for the app.
# Alternate arts of the same card collapse into one entry that remembers every
# collector number it can be found under, so ownership checks still work.

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(r"C:\Users\nvanreet\Downloads\twm")

cards = json.loads((HERE / "sv6_full.json").read_text(encoding="utf-8"))


def sig(c):
    """Same printed card, ignoring which art it is."""
    return (
        c["name"],
        c.get("hp", ""),
        c.get("supertype", ""),
        tuple(a["name"] for a in c.get("attacks", []) or []),
        tuple(a["name"] for a in c.get("abilities", []) or []),
        c.get("evolvesFrom", ""),
        # Trainers with the same name are the same card; text guards the rest
        tuple(c.get("rules", []) or [])[:1],
    )


groups = {}
for n_str, c in cards.items():
    groups.setdefault(sig(c), []).append((int(n_str), c))

entries = []
for s, items in groups.items():
    items.sort()
    n, c = items[0]
    subs = c.get("subtypes", []) or []
    rules = c.get("rules", []) or []
    e = {
        "id": n,
        "nums": [i for i, _ in items],
        "name": c["name"],
        "st": {"Pokémon": "P", "Trainer": "T", "Energy": "E"}.get(c.get("supertype"), "?"),
    }
    if c.get("hp"):
        e["hp"] = int(c["hp"])
    if c.get("types"):
        e["ty"] = c["types"]
    if subs:
        e["sub"] = subs
    if c.get("evolvesFrom"):
        e["from"] = c["evolvesFrom"]
    if c.get("retreatCost"):
        e["rt"] = len(c["retreatCost"])
    ab = [{"n": a["name"], "t": a["text"]} for a in (c.get("abilities") or [])]
    if ab:
        e["ab"] = ab
    # attack cost TYPES matter: several cards attack with energy of a different
    # type than the Pokemon itself (Greninja ex is Fighting but costs Water)
    LETTER = {"Grass": "G", "Fire": "R", "Water": "W", "Lightning": "L",
              "Psychic": "P", "Fighting": "F", "Darkness": "D", "Metal": "M",
              "Fairy": "Y", "Dragon": "N", "Colorless": "C"}
    at = []
    for a in c.get("attacks") or []:
        d = {"n": a["name"], "c": len(a.get("cost") or []), "d": a.get("damage") or "",
             "k": "".join(LETTER.get(t, "C") for t in (a.get("cost") or []))}
        if a.get("text"):
            d["t"] = a["text"]
        at.append(d)
    if at:
        e["at"] = at
    if any("ACE SPEC" in r for r in rules):
        e["ace"] = 1
    # Trainer effect text lives in "rules" alongside generic boilerplate — keep the effect
    BOILER = (
        "You may play any number of Item cards",
        "You may play only 1 Supporter card",
        "You may attach any number of Pokémon Tools",
        "Attach a Pokémon Tool to 1 of your Pokémon",
        "You may play only 1 Stadium card",
        "You can't have more than 1 ACE SPEC card",
        "ACE SPEC: You can't have more than 1",
        "When your Pokémon ex is Knocked Out",
    )
    text = [r for r in rules if not any(b in r for b in BOILER)]
    if text and c.get("supertype") != "Pokémon":
        e["tx"] = " ".join(t.strip() for t in text)
    entries.append(e)

entries.sort(key=lambda e: e["id"])

# what a deck builder needs to know about the pool
pk = [e for e in entries if e["st"] == "P"]
print(f"{len(cards)} printings -> {len(entries)} distinct cards")
print("  Pokemon:", len(pk), " Trainers:", sum(1 for e in entries if e["st"] == "T"),
      " Energy:", sum(1 for e in entries if e["st"] == "E"))
print("  basics:", sum(1 for e in pk if "Basic" in e.get("sub", [])),
      " stage1:", sum(1 for e in pk if "Stage 1" in e.get("sub", [])),
      " stage2:", sum(1 for e in pk if "Stage 2" in e.get("sub", [])),
      " ex:", sum(1 for e in pk if "ex" in e.get("sub", [])))
print("  ACE SPEC:", [e["name"] for e in entries if e.get("ace")])

dupe_names = {}
for e in entries:
    dupe_names.setdefault(e["name"], []).append(e["id"])
print("  same name, different card:",
      {k: v for k, v in dupe_names.items() if len(v) > 1})

payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
js = "/* Twilight Masquerade deck data — generated, do not hand-edit. */\nconst CARDS=" + payload + ";\n"
(REPO / "cards.js").write_text(js, encoding="utf-8")
(HERE / "cards_pretty.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote cards.js", len(js) // 1024, "KB")
