# Deterministic rules check on the generated decks, then emit decks.js.
# The model designs; this script decides what is legal.

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(r"C:\Users\nvanreet\Downloads\twm")

cards = json.loads((HERE / "cards_pretty.json").read_text(encoding="utf-8"))
by_id = {c["id"]: c for c in cards}
by_name = {}
for c in cards:
    by_name.setdefault(c["name"], []).append(c)

src = HERE / (sys.argv[1] if len(sys.argv) > 1 else "deck_raw.json")
payload = json.loads(src.read_text(encoding="utf-8"))
print(f"validating {src.name}")
decks, combos = payload["decks"], payload.get("combos", [])

fatal = 0
for d in decks:
    errs, warns = [], []
    total = d["energy"]
    name_counts, aces, basics = {}, 0, 0

    for entry in d["cards"]:
        c = by_id.get(entry["id"])
        if c is None:
            errs.append(f"id {entry['id']} is not in this set ({entry['name']})")
            continue
        if c["name"] != entry["name"]:
            # trust the id only if the name also exists somewhere
            if entry["name"] in by_name:
                errs.append(f"id {entry['id']} is {c['name']}, not {entry['name']}")
            else:
                errs.append(f"no card named {entry['name']} in this set")
            continue
        n = entry["count"]
        if n < 1:
            errs.append(f"{entry['name']} has count {n}")
        total += n
        name_counts[c["name"]] = name_counts.get(c["name"], 0) + n
        if c.get("ace"):
            aces += n
        if c["st"] == "P" and "Basic" in c.get("sub", []):
            basics += n

    for nm, n in name_counts.items():
        if n > 4:
            errs.append(f"{n} copies of {nm} (limit 4)")
    if aces > 1:
        errs.append(f"{aces} ACE SPEC cards (limit 1)")
    if basics == 0:
        errs.append("no Basic Pokemon")
    elif basics < 8:
        warns.append(f"only {basics} Basic Pokemon")
    if total != 60:
        errs.append(f"{total} cards, must be 60 (energy {d['energy']} included)")

    # evolution support
    for entry in d["cards"]:
        c = by_id.get(entry["id"])
        if not c or not c.get("from"):
            continue
        have = sum(
            e["count"] for e in d["cards"]
            if by_id.get(e["id"]) and by_id[e["id"]]["name"] == c["from"]
        )
        if have < entry["count"]:
            errs.append(f"{entry['count']} {c['name']} but {have} {c['from']}")

    status = "FAIL" if errs else ("ok" if not warns else "ok*")
    print(f"[{status}] {d['key']:<10} {d['name']}  "
          f"({sum(e['count'] for e in d['cards'])} cards + {d['energy']} energy)")
    for e in errs:
        print("    ERROR:", e)
    for w in warns:
        print("    note :", w)
    if d.get("judgeProblems"):
        print("    judge flagged:", len(d["judgeProblems"]), "item(s)")
    fatal += len(errs)

# combos must reference real cards
for cb in combos:
    bad = [i for i in cb["ids"] if i not in by_id]
    if bad:
        print(f"[FAIL] combo '{cb['title']}' references missing ids {bad}")
        fatal += 1

if fatal:
    print(f"\n{fatal} problem(s) — decks.js NOT written")
    sys.exit(1)

clean = []
for d in decks:
    entry = {
        "key": d["key"], "name": d["name"], "emoji": d["emoji"],
        "level": d["level"], "strategy": d["strategy"], "energy": d["energy"],
        "cards": [{"id": e["id"], "name": e["name"], "count": e["count"]} for e in d["cards"]],
        "combos": d["combos"], "upgrade": d["upgrade"],
    }
    if d.get("energySplit"):
        assert sum(d["energySplit"].values()) == d["energy"], f'{d["key"]}: split mismatch'
        entry["energySplit"] = d["energySplit"]
    clean.append(entry)
js = ("/* Twilight Masquerade suggested decks — generated and rules-checked. */\n"
      "const DECKS=" + json.dumps(clean, ensure_ascii=False, separators=(",", ":")) + ";\n"
      "const COMBOS=" + json.dumps(combos, ensure_ascii=False, separators=(",", ":")) + ";\n")
(REPO / "decks.js").write_text(js, encoding="utf-8")
print(f"\nall decks legal — wrote decks.js ({len(js)//1024} KB, {len(clean)} decks, {len(combos)} combos)")
