# Download every TWM card image (EN/FR/JP) for the scanner descriptor build.
import concurrent.futures as cf
import os, re, sys, time, urllib.request

SP = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SP, "scan_imgs")
IDX = r"C:\Users\nvanreet\Downloads\twm\index.html"

html = open(IDX, encoding="utf-8").read()
m = re.search(r"const JPX=\{(.*?)\};", html, re.S)
jpx = dict(re.findall(r'(\d+):\["([^"]+)"', m.group(1)))
print("JPX entries:", len(jpx))

jobs = []
for n in range(1, 227):
    jobs.append(("en", n, f"https://images.pokemontcg.io/sv6/{n}.png", f"{n}.png"))
    jobs.append(("fr", n, f"https://assets.tcgdex.net/fr/sv/sv06/{n:03d}/low.webp", f"{n}.webp"))
    if str(n) in jpx:
        jobs.append(("ja", n, f"https://assets.tcgdex.net/ja/SV/{jpx[str(n)]}/low.webp", f"{n}.webp"))

for lang in ("en", "fr", "ja"):
    os.makedirs(os.path.join(OUT, lang), exist_ok=True)

def grab(job):
    lang, n, url, fn = job
    path = os.path.join(OUT, lang, fn)
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return "cached"
    for t in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "twm-scan-build"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) > 2000:
                open(path, "wb").write(data)
                return "ok"
        except Exception as e:
            err = str(e)[:60]
            time.sleep(1.5 * (t + 1))
    return f"FAIL {lang}/{n}: {err}"

with cf.ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(grab, jobs))

ok = sum(1 for r in res if r in ("ok", "cached"))
fails = [r for r in res if r.startswith("FAIL")]
print(f"{ok}/{len(jobs)} images present")
for f in fails[:20]:
    print(f)
sys.exit(1 if fails else 0)
