#!/usr/bin/env python3
"""Assemble the 2026-09-27 edition of Meme Reality Check.

Reads:
  ~/workspace/meme-gather/left_memes.md   (59 entries, ## N.)
  ~/workspace/meme-gather/right_memes.md  (50 entries, ### RN.)
  ~/workspace/meme-gather/fc_*.md         (verdict/reality/sources)
  ~/workspace/meme-reality-check/editions/2026-09-27/images/ (downloaded)
Writes:
  ~/workspace/meme-reality-check/editions/2026-09-27/edition.json
  ~/workspace/meme-reality-check/editions/2026-09-27/memes.json
  images/<NEWID>.jpg for all 100 (downloaded or generated text cards)
"""
import json, os, re, shutil
from PIL import Image, ImageDraw, ImageFont

GATHER = os.path.expanduser("~/workspace/meme-gather")
ED = os.path.expanduser("~/workspace/meme-reality-check/editions/2026-09-27")
IMGDIR = os.path.join(ED, "images")

def parse_memes(path, hdr_re, prefix):
    entries, cur = {}, None
    with open(path) as f:
        for line in f:
            m = re.match(hdr_re, line)
            if m:
                cur = f"{prefix}{m.group(1)}"
                entries[cur] = {"title": m.group(2).strip()}
            elif cur and line.startswith("- "):
                k, _, v = line[2:].partition(":")
                entries[cur][k.strip()] = v.strip()
    return entries

left = parse_memes(f"{GATHER}/left_memes.md", r"## (\d+)\.\s+(.*)", "L")
right = parse_memes(f"{GATHER}/right_memes.md", r"### R(\d+)\.\s+(.*)", "R")

def parse_fc(path):
    out, cur = {}, None
    with open(path) as f:
        for line in f:
            m = re.match(r"## ([LR]\d+)\s*$", line)
            if m:
                cur = m.group(1); out[cur] = {"sources": []}
            elif cur and line.startswith("verdict:"):
                out[cur]["verdict"] = line.split(":", 1)[1].strip()
            elif cur and line.startswith("reality:"):
                out[cur]["reality"] = line.split(":", 1)[1].strip()
            elif cur and line.startswith("- ") and "sources" not in line:
                s = line[2:].strip()
                if s.startswith("("):  # "(no sources needed...)"
                    continue
                name, _, url = s.rpartition(" — ")
                if not url.startswith("http"):
                    name, _, url = s.rpartition(" - ")
                out[cur]["sources"].append({"name": name.strip() or "source",
                                            "url": url.strip()})
    return out

fc = {}
for fn in ["fc_left_1_20.md", "fc_left_21_40.md", "fc_left_41_59.md",
           "fc_right_1_25.md", "fc_right_26_50.md"]:
    fc.update(parse_fc(f"{GATHER}/{fn}"))

print(f"memes: L={len(left)} R={len(right)}; factchecks={len(fc)}")

def engagement(e):
    t = e.get("traction", "")
    m = re.search(r"([\d.]+)\s*([KM])?\+?\s*(likes|upvotes|views)", t, re.I)
    if not m:
        return 0
    n = float(m.group(1))
    if (m.group(2) or "").upper() == "K": n *= 1e3
    if (m.group(2) or "").upper() == "M": n *= 1e6
    return n

def source_name(eid, e):
    if eid.startswith("R"):
        n = int(eid[1:])
        if 1 <= n <= 15:
            return "r/ConservativeMemes"
    t = e.get("title", "")
    name = t.split(" — ")[0].strip().strip('"')
    return name or "source"

# --- select 50 left: all checkable first, then top no-claim by traction ---
checkable, jokes = [], []
for eid in sorted(left, key=lambda x: int(x[1:])):
    v = fc.get(eid, {}).get("verdict", "no-claim")
    (checkable if v != "no-claim" else jokes).append(eid)
jokes.sort(key=lambda x: engagement(left[x]), reverse=True)
sel_left = checkable + jokes[:50 - len(checkable)]
sel_left.sort(key=lambda x: int(x[1:]))
sel_right = sorted(right, key=lambda x: int(x[1:]))
print(f"selected: L={len(sel_left)} (checkable={len(checkable)}, jokes kept={len(sel_left)-len(checkable)}) R={len(sel_right)}")
dropped = [e for e in left if e not in sel_left]
print("dropped left:", ", ".join(f"{d}({engagement(left[d]):.0f})" for d in dropped))

# --- map downloaded images ---
dl = {}
for fn in os.listdir(IMGDIR):
    base, ext = os.path.splitext(fn)
    key = base[1:] if base.startswith("RR") else base  # RR1 -> R1
    dl[key] = fn

def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def text_card(text, src, dest):
    W = 1080
    img = Image.new("RGB", (W, W), (22, 26, 35))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 150], fill=(30, 34, 48))
    f_head, f_body, f_foot = font(44), font(46), font(34)
    d.text((60, 48), "MEME TEXT", font=f_head, fill=(124, 92, 255))
    words, lines, line = text.split(), [], ""
    for w in words:
        t = (line + " " + w).strip()
        if d.textlength(t, font=f_body) < W - 120:
            line = t
        else:
            lines.append(line); line = w
    lines.append(line)
    lines = lines[:22]
    y = 220
    for ln in lines:
        d.text((60, y), ln, font=f_body, fill=(232, 235, 242))
        y += 64
    d.text((60, W - 90), f"Source: {src[:60]}", font=f_foot, fill=(154, 163, 184))
    img.save(dest, "JPEG", quality=88)

memes = []
order = 0
for side, sel, pre in [("left", sel_left, "L"), ("right", sel_right, "R")]:
    for i, old in enumerate(sel, 1):
        new = f"{pre}{i:02d}"
        e, f = (left if side == "left" else right)[old], fc.get(old, {})
        verdict = f.get("verdict", "no-claim")
        claim_raw = e.get("claim", "")
        claim = "" if verdict == "no-claim" else re.sub(r"^CHECKABLE.*?[—–]\s*", "", claim_raw)
        dest = os.path.join(IMGDIR, f"{new}.jpg")
        if old in dl and not os.path.exists(dest):
            src = os.path.join(IMGDIR, dl[old])
            try:
                im = Image.open(src).convert("RGB")
                im.save(dest, "JPEG", quality=90)
            except Exception as ex:
                print("convert fail", old, ex)
                text_card(e.get("meme_text", "")[:600], source_name(old, e), dest)
        elif old not in dl:
            text_card(e.get("meme_text", "")[:600], source_name(old, e), dest)
        order += 1
        memes.append({
            "id": new, "side": side, "image": f"images/{new}.jpg",
            "source_name": source_name(old, e),
            "source_url": e.get("source_url", ""),
            "traction": e.get("traction", ""),
            "meme_text": e.get("meme_text", ""),
            "claim": claim, "verdict": verdict,
            "reality": f.get("reality", ""),
            "sources": f.get("sources", []),
            "order": order,
        })

# remove stale non-selected images
keep = {m["image"].split("/")[-1] for m in memes}
for fn in os.listdir(IMGDIR):
    if fn not in keep:
        os.remove(os.path.join(IMGDIR, fn))

with open(os.path.join(ED, "memes.json"), "w") as f:
    json.dump(memes, f, indent=1, ensure_ascii=False)
with open(os.path.join(ED, "edition.json"), "w") as f:
    json.dump({
        "title": "September 27, 2026",
        "date_label": "Sunday, September 27, 2026",
        "description": "50 left-source memes and 50 right-source memes, checked against the record. Same rules for both sides."
    }, f, indent=1)

from collections import Counter
c = Counter((m["side"], m["verdict"]) for m in memes)
print("verdicts:", dict(c))
print("images:", len([f for f in os.listdir(IMGDIR) if f.endswith('.jpg')]))
missing = [m["id"] for m in memes if not m["reality"]]
print("missing reality:", missing)
