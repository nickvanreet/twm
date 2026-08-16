# Scanner v2: dual descriptors (whole card + art window) and a JS-mirrored
# multi-hypothesis search, evaluated under a much harsher photo simulation.
import os, io, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

SP = os.path.dirname(os.path.abspath(__file__))
IMGS = os.path.join(SP, "scan_imgs")
H = 16
CG = 6
ART = (0.055, 0.105, 0.945, 0.465)   # art window, fractions of the card
PAD = 0.18                            # capture margin around the guide frame
rng = random.Random(99)

def to_gray(a):
    return a[:, :, 0]*0.299 + a[:, :, 1]*0.587 + a[:, :, 2]*0.114

def descriptor(img):
    gh = to_gray(np.asarray(img.resize((H+1, H), Image.BILINEAR), np.float32))
    gv = to_gray(np.asarray(img.resize((H, H+1), Image.BILINEAR), np.float32))
    bits = np.concatenate([(gh[:, 1:] > gh[:, :-1]).flatten(),
                           (gv[1:, :] > gv[:-1, :]).flatten()])
    c = np.asarray(img.resize((CG, CG), Image.BILINEAR), np.float32).reshape(-1)
    return np.packbits(bits), c - c.mean()

def art_crop(img):
    w, h = img.size
    return img.crop((round(ART[0]*w), round(ART[1]*h), round(ART[2]*w), round(ART[3]*h)))

def dual(img):
    return descriptor(img), descriptor(art_crop(img))

def load_all():
    entries = []
    for lang in ("en", "fr", "ja"):
        d = os.path.join(IMGS, lang)
        for fn in sorted(os.listdir(d), key=lambda f: int(f.split(".")[0])):
            img = Image.open(os.path.join(d, fn)).convert("RGB")
            (wb, wc), (ab, ac) = dual(img)
            entries.append((lang, int(fn.split(".")[0]), wb, wc, ab, ac))
    return entries

# ---------------- harsher phone-photo simulation ----------------
def fake_background(w, h):
    base = np.zeros((h, w, 3), np.float32)
    base[:, :, 0] = rng.uniform(50, 170); base[:, :, 1] = rng.uniform(35, 130)
    base[:, :, 2] = rng.uniform(20, 110)
    base += np.random.normal(0, 10, base.shape)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

def perturb_padded(img):
    """Return the padded capture the phone would take: card somewhere inside
    the guide area, off in scale/position/rotation, with photo damage."""
    w0, h0 = img.size
    s = 300 / w0
    img = img.resize((300, round(h0*s)), Image.BILINEAR)
    w, h = img.size
    fw, fh = round(w*(1+2*PAD)), round(h*(1+2*PAD))       # padded field
    bg = fake_background(fw, fh)
    jx, jy = w*0.04, h*0.04                                # perspective
    quad = []
    for cx, cy in [(0, 0), (0, h), (w, h), (w, 0)]:
        quad += [cx+rng.uniform(-jx, jx), cy+rng.uniform(-jy, jy)]
    card = img.transform((w, h), Image.QUAD, quad, Image.BILINEAR)
    scale = rng.uniform(0.78, 1.18)                        # card size vs frame
    card = card.resize((round(w*scale), round(h*scale)), Image.BILINEAR)
    card = card.rotate(rng.uniform(-6, 6), Image.BILINEAR, expand=True,
                       fillcolor=(80, 60, 45))
    cx = round(fw/2 - card.width/2 + rng.uniform(-0.10, 0.10)*w)
    cy = round(fh/2 - card.height/2 + rng.uniform(-0.10, 0.10)*h)
    bg.paste(card, (cx, cy))
    out = bg
    out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.55, 1.45))
    out = ImageEnhance.Contrast(out).enhance(rng.uniform(0.7, 1.3))
    a = np.asarray(out, np.float32)
    a[:, :, 0] *= rng.uniform(0.85, 1.15); a[:, :, 2] *= rng.uniform(0.85, 1.15)
    ramp = np.linspace(rng.uniform(-35, 35), rng.uniform(-35, 35), a.shape[1])
    a += ramp[None, :, None]
    a += np.random.normal(0, rng.uniform(2, 6), a.shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if rng.random() < 0.75:                                # sleeve glare
        g = Image.new("L", out.size, 0); dr = ImageDraw.Draw(g)
        for _ in range(rng.randint(1, 3)):
            gx, gy = rng.uniform(0, out.width), rng.uniform(0, out.height)
            gw, gh2 = rng.uniform(30, 110), rng.uniform(15, 60)
            dr.ellipse([gx-gw, gy-gh2, gx+gw, gy+gh2], fill=rng.randint(60, 150))
        g = g.filter(ImageFilter.GaussianBlur(20))
        out = Image.composite(Image.new("RGB", out.size, (255, 255, 255)), out, g)
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 1.8)))
    buf = io.BytesIO(); out.save(buf, "JPEG", quality=rng.randint(50, 88))
    return Image.open(buf).convert("RGB")

# ---------------- matcher (mirrors the JS implementation) ----------------
class DB:
    def __init__(self, entries, wcol=6.0, wart=2.0):
        self.wcol, self.wart = wcol, wart
        self.nums = np.array([e[1] for e in entries])
        self.langs = [e[0] for e in entries]
        self.wh = np.stack([np.unpackbits(e[2]) for e in entries]).astype(np.int16)
        self.wc = np.stack([e[3] for e in entries])
        self.ah = np.stack([np.unpackbits(e[4]) for e in entries]).astype(np.int16)
        self.ac = np.stack([e[5] for e in entries])

    def ham_whole(self, wb):
        q = np.unpackbits(wb).astype(np.int16)
        return np.abs(self.wh - q[None, :]).sum(1)

    def full_scores(self, wdesc, adesc):
        (wb, wc), (ab, ac) = wdesc, adesc
        qw = np.unpackbits(wb).astype(np.int16)
        qa = np.unpackbits(ab).astype(np.int16)
        sw = np.abs(self.wh - qw[None, :]).sum(1) + self.wcol*np.abs(self.wc - wc[None, :]).mean(1)
        sa = np.abs(self.ah - qa[None, :]).sum(1) + self.wcol*np.abs(self.ac - ac[None, :]).mean(1)
        return sw + self.wart*sa

def frame_crop(padded, s, dx, dy):
    """The guide-frame rectangle inside the padded capture, scaled/offset."""
    fw, fh = padded.size
    w = fw/(1+2*PAD); h = fh/(1+2*PAD)
    cx = fw/2 + dx*w; cy = fh/2 + dy*h
    hw = w*s/2; hh = h*s/2
    return padded.crop((round(cx-hw), round(cy-hh), round(cx+hw), round(cy+hh)))

def recognize(db, padded, coarse_keep=4, rots=(-4, 0, 4)):
    hyps = []
    for s in (0.86, 1.0, 1.14):
        for dx in (-0.08, 0, 0.08):
            for dy in (-0.08, 0, 0.08):
                crop = frame_crop(padded, s, dx, dy)
                wb, _ = descriptor(crop)
                hyps.append((self_min(db, wb), s, dx, dy))
    hyps.sort(key=lambda x: x[0])
    best = {}
    for _, s, dx, dy in hyps[:coarse_keep]:
        for rot in rots:
            crop = frame_crop(padded, s, dx, dy)
            if rot: crop = crop.rotate(rot, Image.BILINEAR, fillcolor=(60, 50, 40))
            sc = db.full_scores(*[d for d in dual(crop)])
            for i in np.argsort(sc)[:12]:
                key = int(i)
                if key not in best or sc[key] < best[key]:
                    best[key] = float(sc[key])
    order = sorted(best.items(), key=lambda kv: kv[1])
    seen, top = set(), []
    for i, sc in order:
        n = int(db.nums[i])
        if n in seen: continue
        seen.add(n); top.append((n, db.langs[i], sc))
        if len(top) == 5: break
    return top

def self_min(db, wb):
    return int(db.ham_whole(wb).min())

def recognize_old(db, padded):
    """v1 behaviour: single centre crop, whole-card score only."""
    crop = frame_crop(padded, 1.0, 0, 0)
    (wb, wc), _ = dual(crop)
    q = np.unpackbits(wb).astype(np.int16)
    sc = np.abs(db.wh - q[None, :]).sum(1) + db.wcol*np.abs(db.wc - wc[None, :]).mean(1)
    order = np.argsort(sc)
    seen, top = set(), []
    for i in order:
        n = int(db.nums[i])
        if n in seen: continue
        seen.add(n); top.append(n)
        if len(top) == 5: break
    return top

def evaluate(entries, wart, trials=1, seed=5, also_old=False):
    global rng
    rng = random.Random(seed); np.random.seed(seed)
    db = DB(entries, wart=wart)
    t1 = t5 = o1 = o5 = total = 0
    margins_ok, margins_bad = [], []
    for lang, num, *_ in entries:
        src = Image.open(os.path.join(
            IMGS, lang, f"{num}.{'png' if lang=='en' else 'webp'}")).convert("RGB")
        for _ in range(trials):
            padded = perturb_padded(src)
            top = recognize(db, padded)
            total += 1
            if top and top[0][0] == num:
                t1 += 1
                if len(top) > 1: margins_ok.append(top[1][2]-top[0][2])
            elif top:
                margins_bad.append(top[1][2]-top[0][2] if len(top) > 1 else 0)
            if num in [t[0] for t in top]: t5 += 1
            if also_old:
                old = recognize_old(db, padded)
                if old and old[0] == num: o1 += 1
                if num in old: o5 += 1
    line = f"wart={wart}  NEW top1 {t1/total:.3%} top5 {t5/total:.3%}"
    if also_old:
        line += f"   OLD top1 {o1/total:.3%} top5 {o5/total:.3%}"
    print(line, flush=True)
    if margins_ok:
        print(f"  margin when right: p10 {np.percentile(margins_ok,10):.0f}  "
              f"median {np.median(margins_ok):.0f}; "
              f"when wrong: median {np.median(margins_bad) if margins_bad else 0:.0f}",
              flush=True)
    return t1/total, t5/total

if __name__ == "__main__":
    print("building dual descriptors...", flush=True)
    entries = load_all()
    print("entries:", len(entries), flush=True)
    evaluate(entries, wart=2.0, trials=1, seed=5, also_old=True)
    for wart in (1.0, 3.0):
        evaluate(entries, wart=wart, trials=1, seed=5)
