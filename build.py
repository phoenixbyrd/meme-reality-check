#!/usr/bin/env python3
"""Meme Reality Check static site generator.

Reads editions/<YYYY-MM-DD>/edition.json + memes.json (+ images/),
writes a modern static site into docs/ ready for GitHub Pages.

- / : latest edition (card grid with side/verdict filters)
- /editions/<date>/ : that day's edition
- /archive.html : past editions

memes.json entry:
  {id, side ("left"|"right"), image, source_name, source_url, traction,
   meme_text, claim, verdict, reality, sources:[{name,url}], order}
verdict: accurate | mostly-accurate | mixed | misleading | false | no-claim
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EDITIONS = os.path.join(ROOT, "editions")
SITE = os.path.join(ROOT, "docs")
BASE_URL = "https://phoenixbyrd.github.io/meme-reality-check"


def esc(s):
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


VERDICTS = {
    "accurate":        ("Accurate", "#22c55e"),
    "mostly-accurate": ("Mostly accurate", "#a3e635"),
    "mixed":           ("Mixed", "#fbbf24"),
    "misleading":      ("Misleading", "#fb923c"),
    "false":           ("False", "#ef4444"),
    "no-claim":        ("Just a joke — no factual claim", "#9ca3af"),
}
VERDICT_ORDER = ["accurate", "mostly-accurate", "mixed", "misleading", "false", "no-claim"]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0f14;--card:#161a23;--card2:#1d2230;--line:#262c3d;--txt:#e8ebf2;--mut:#9aa3b8;--acc:#7c5cff}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--txt);line-height:1.6;min-height:100vh}
a{color:#8ea6ff;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.site{background:rgba(13,15,20,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:50}
header.site .wrap{display:flex;align-items:center;justify-content:space-between}
.brand{font-size:21px;font-weight:800;letter-spacing:.3px;color:#fff}
.brand .m1{background:linear-gradient(135deg,#7c5cff,#00d4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand .m2{color:#ff5c7a}
.tagline{font-size:12px;color:var(--mut);margin-top:1px}
nav a{color:var(--mut);font-size:14px;margin-left:20px}
nav a:hover{color:#fff}
.hero{padding:44px 0 10px;text-align:center}
.hero .kicker{display:inline-block;font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--acc);border:1px solid var(--acc);border-radius:999px;padding:5px 14px;margin-bottom:16px}
.hero h1{font-size:clamp(30px,5vw,52px);line-height:1.1;font-weight:800;margin-bottom:12px}
.hero h1 .grad{background:linear-gradient(135deg,#7c5cff,#00d4ff 60%,#22c55e);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{color:var(--mut);max-width:640px;margin:0 auto;font-size:16px}
.stats{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:22px 0 6px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 16px;font-size:13px;color:var(--mut)}
.stat b{font-size:20px;display:block;color:#fff}
.filters{position:sticky;top:62px;z-index:40;background:rgba(13,15,20,.9);backdrop-filter:blur(12px);padding:14px 0;border-bottom:1px solid var(--line);margin-top:18px}
.filters .wrap{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.fbtn{background:var(--card);border:1px solid var(--line);color:var(--mut);border-radius:999px;padding:7px 16px;font-size:13px;cursor:pointer;transition:.15s}
.fbtn:hover{border-color:var(--acc);color:#fff}
.fbtn.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.fsep{width:1px;height:22px;background:var(--line);margin:0 4px}
.fcount{margin-left:auto;font-size:13px;color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;padding:26px 0 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,border-color .15s}
.card:hover{transform:translateY(-3px);border-color:#3a4360}
.card.hidden{display:none}
.memeimg{width:100%;aspect-ratio:1/1;object-fit:cover;background:#0a0c10;cursor:zoom-in;display:block}
.card .body{padding:16px 18px 18px;display:flex;flex-direction:column;gap:10px;flex:1}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.side{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border-radius:999px;padding:4px 11px}
.side.left{background:rgba(96,165,250,.14);color:#7fb3ff;border:1px solid rgba(96,165,250,.4)}
.side.right{background:rgba(248,113,113,.13);color:#ff9d9d;border:1px solid rgba(248,113,113,.4)}
.verdict{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border-radius:999px;padding:4px 11px;border:1px solid}
.claim{font-size:14px;color:var(--mut);font-style:italic;border-left:3px solid var(--line);padding-left:12px}
.claim b{color:var(--txt);font-style:normal;display:block;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.reality{font-size:14px;color:var(--txt)}
.reality b{display:block;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--mut);margin-bottom:4px}
.srcs{font-size:12px;color:var(--mut);margin-top:auto;padding-top:8px;border-top:1px dashed var(--line)}
.srcs a{margin-right:10px}
.trsrc{font-size:12px;color:var(--mut)}
.trsrc a{color:var(--mut);text-decoration:underline}
.how{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin:10px 0 40px;font-size:14px;color:var(--mut)}
.how h2{color:#fff;font-size:18px;margin-bottom:10px}
.how li{margin:6px 0 6px 18px}
footer.site{border-top:1px solid var(--line);padding:26px 0;margin-top:10px;font-size:13px;color:var(--mut)}
.archive-list{list-style:none;padding:24px 0 40px}
.archive-list li{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 22px;margin-bottom:12px}
.archive-list .d{font-size:13px;color:var(--mut)}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;align-items:center;justify-content:center;z-index:100;cursor:zoom-out;padding:24px}
.lightbox.open{display:flex}
.lightbox img{max-width:100%;max-height:100%;border-radius:12px}
.ednav{display:flex;justify-content:space-between;padding:8px 0 30px;font-size:14px}
.dateline{font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--mut);text-align:center;margin-top:26px}
@media(max-width:640px){.fcount{display:none}.filters{top:60px}}
"""

JS = """
const sideBtns=[...document.querySelectorAll('[data-side]')];
const verBtns=[...document.querySelectorAll('[data-verdict]')];
let side='all',verdict='all';
function apply(){
  let n=0;
  document.querySelectorAll('.card').forEach(c=>{
    const okS=side==='all'||c.dataset.side===side;
    const okV=verdict==='all'||c.dataset.verdict===verdict;
    const show=okS&&okV;
    c.classList.toggle('hidden',!show);
    if(show)n++;
  });
  document.getElementById('fcount').textContent=n+' shown';
}
sideBtns.forEach(b=>b.onclick=()=>{side=b.dataset.side;sideBtns.forEach(x=>x.classList.toggle('on',x===b));apply();});
verBtns.forEach(b=>b.onclick=()=>{verdict=b.dataset.verdict;verBtns.forEach(x=>x.classList.toggle('on',x===b));apply();});
const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.querySelectorAll('.memeimg').forEach(im=>im.onclick=()=>{lbi.src=im.src;lb.classList.add('open');});
lb.onclick=()=>lb.classList.remove('open');
document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.classList.remove('open');});
apply();
"""

PAGE_TOP = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Meme Reality Check</title>
<meta name="description" content="Daily fact-check of trending political memes from left- and right-leaning sources. The reality behind the meme.">
<style>""" + CSS + """</style></head>
<body>
"""

HEADER = """<header class="site"><div class="wrap">
<div><a class="brand" href="{base}/"><span class="m1">MEME</span> <span class="m2">VS</span> <span class="m1">REALITY</span></a><div class="tagline">The reality behind the meme.</div></div>
<nav><a href="{base}/">Today</a><a href="{base}/archive.html">Archive</a><a href="{base}/#how">Method</a></nav>
</div></header>"""

FOOTER = """<footer class="site"><div class="wrap">
<strong style="color:#fff">Meme Reality Check</strong> — every day we pull trending political memes from left-leaning and right-leaning sources and check the claims behind them against named sources. Same rules for both sides.<br>
<span style="font-size:12px">Memes belong to their creators; shown here for commentary and fact-checking. Corrections: reply in the Muse app.</span>
</div></footer>
<div class="lightbox" id="lb"><img id="lbi" alt="meme enlarged"></div>
<script>""" + JS + """</script>
</body></html>"""

HOW = """<div class="how" id="how"><h2>How we rate</h2>
<ul>
<li><strong style="color:#fff">Where the memes come from.</strong> Each day we collect the most-shared political memes from left-leaning sources and right-leaning sources. The "trending left / trending right" badge says where a meme is circulating — not whether it's true.</li>
<li><strong style="color:#fff">What we check.</strong> We pull out the factual claim inside the meme and check it against named, published sources. Memes that are pure jokes or opinions get "Just a joke — no factual claim" instead of a fake verdict.</li>
<li><strong style="color:#fff">Same rules for both sides.</strong> A false claim from the left and a false claim from the right get the same treatment. We don't infer motives, we don't do partisan framing, and when sources disagree or something is unknown, we say so.</li>
</ul></div>"""


def verdict_chip(v):
    label, color = VERDICTS.get(v, VERDICTS["no-claim"])
    return (f'<span class="verdict" style="color:{color};border-color:{color}55;'
            f'background:{color}14">&#9679; {esc(label)}</span>')


def side_badge(side):
    if side == "left":
        return '<span class="side left">Trending left</span>'
    return '<span class="side right">Trending right</span>'


def card(m, date):
    img_url = f"{BASE_URL}/editions/{date}/{m['image']}"
    srcs = " ".join(
        f'<a href="{esc(s.get("url", "#"))}" target="_blank" rel="noopener">{esc(s.get("name", "source"))}</a>'
        for s in m.get("sources", []))
    claim_html = (f'<div class="claim"><b>The claim</b>{esc(m.get("claim") or "No checkable factual claim — just a joke or opinion.")}</div>'
                  if m.get("verdict") != "no-claim" else "")
    return f"""<div class="card" data-side="{m['side']}" data-verdict="{m['verdict']}">
<img class="memeimg" loading="lazy" src="{img_url}" alt="political meme">
<div class="body">
<div class="badges">{side_badge(m['side'])}{verdict_chip(m['verdict'])}</div>
{claim_html}
<div class="reality"><b>The reality</b>{esc(m.get('reality', ''))}</div>
<div class="srcs"><strong>Sources:</strong> {srcs if srcs else "—"}</div>
<div class="trsrc">Via <a href="{esc(m.get('source_url', '#'))}" target="_blank" rel="noopener">{esc(m.get('source_name', 'source'))}</a>{' · ' + esc(m['traction']) if m.get('traction') else ''}</div>
</div></div>"""


def edition_page(date, edition, memes, prev_date, next_date):
    cards = "\n".join(card(m, date) for m in sorted(memes, key=lambda x: x.get("order", 0)))
    counts = {v: 0 for v in VERDICTS}
    for m in memes:
        counts[m.get("verdict", "no-claim")] = counts.get(m.get("verdict", "no-claim"), 0) + 1
    left_n = sum(1 for m in memes if m["side"] == "left")
    right_n = sum(1 for m in memes if m["side"] == "right")
    stat_cells = "".join(
        f'<div class="stat"><b style="color:{VERDICTS[v][1]}">{counts[v]}</b>{VERDICTS[v][0]}</div>'
        for v in VERDICT_ORDER if counts[v])
    ver_btns = "".join(
        f'<button class="fbtn" data-verdict="{v}">{VERDICTS[v][0]}</button>'
        for v in VERDICT_ORDER)
    nav = []
    if prev_date:
        nav.append(f'<a href="{BASE_URL}/editions/{prev_date}/">&larr; {prev_date}</a>')
    else:
        nav.append('<span></span>')
    if next_date:
        nav.append(f'<a href="{next_date}">{next_date} &rarr;</a>')
    else:
        nav.append(f'<a href="{BASE_URL}/archive.html">Archive &rarr;</a>')
    return (PAGE_TOP.format(title=edition["title"]) + HEADER.format(base=BASE_URL) + f"""
<div class="wrap">
<div class="dateline">{esc(edition['date_label'])} &middot; Daily edition</div>
<div class="hero">
<span class="kicker">Daily meme fact-check</span>
<h1>The memes, <span class="grad">minus the spin.</span></h1>
<p>{esc(edition['description'])}</p>
<div class="stats">
<div class="stat"><b>{left_n}</b>from left-leaning sources</div>
<div class="stat"><b>{right_n}</b>from right-leaning sources</div>
{stat_cells}
</div>
</div>
</div>
<div class="filters"><div class="wrap">
<button class="fbtn on" data-side="all">All</button>
<button class="fbtn" data-side="left">Trending left</button>
<button class="fbtn" data-side="right">Trending right</button>
<span class="fsep"></span>
<button class="fbtn on" data-verdict="all">Any verdict</button>
{ver_btns}
<span class="fcount" id="fcount"></span>
</div></div>
<div class="wrap">
<div class="grid">{cards}</div>
{HOW}
<div class="ednav">{nav[0]}{nav[1]}</div>
</div>
{FOOTER}""")


def archive_page(items):
    lis = "".join(
        f"""<li><a href="{BASE_URL}/editions/{d}/"><strong style="color:#fff">{esc(ed['title'])}</strong></a>
<div class="d">{esc(ed['date_label'])} &middot; {ed.get('left_n', 0)} left-source memes, {ed.get('right_n', 0)} right-source memes checked</div></li>"""
        for d, ed in items)
    return (PAGE_TOP.format(title="Archive") + HEADER.format(base=BASE_URL) + f"""
<div class="wrap">
<div class="dateline">Archive</div>
<div class="hero"><h1>Past <span class="grad">editions.</span></h1></div>
<ul class="archive-list">{lis}</ul>
</div>
{FOOTER}""")


def main():
    dates = sorted([d for d in os.listdir(EDITIONS)
                    if os.path.isdir(os.path.join(EDITIONS, d))
                    and os.path.exists(os.path.join(EDITIONS, d, "memes.json"))],
                   reverse=True)
    if not dates:
        print("no editions", file=sys.stderr)
        sys.exit(1)
    os.makedirs(SITE, exist_ok=True)

    editions = {}
    for d in dates:
        with open(os.path.join(EDITIONS, d, "edition.json")) as f:
            edition = json.load(f)
        with open(os.path.join(EDITIONS, d, "memes.json")) as f:
            memes = json.load(f)
        editions[d] = (edition, memes)
        # copy images
        src_img = os.path.join(EDITIONS, d, "images")
        dst_img = os.path.join(SITE, "editions", d)
        if os.path.isdir(src_img):
            for fn in os.listdir(src_img):
                os.makedirs(dst_img, exist_ok=True)
                shutil.copy2(os.path.join(src_img, fn), os.path.join(dst_img, fn))
        edition["left_n"] = sum(1 for m in memes if m["side"] == "left")
        edition["right_n"] = sum(1 for m in memes if m["side"] == "right")

    for i, d in enumerate(dates):
        edition, memes = editions[d]
        prev_d = dates[i + 1] if i + 1 < len(dates) else None
        next_d = dates[i - 1] if i - 1 >= 0 else None
        out_dir = os.path.join(SITE, "editions", d)
        os.makedirs(out_dir, exist_ok=True)
        html = edition_page(d, edition, memes, prev_d, next_d)
        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write(html)
        if i == 0:  # latest edition is also the homepage
            with open(os.path.join(SITE, "index.html"), "w") as f:
                f.write(html)

    with open(os.path.join(SITE, "archive.html"), "w") as f:
        f.write(archive_page([(d, editions[d][0]) for d in dates]))
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    print(f"built {len(dates)} edition(s): {', '.join(dates)}")


if __name__ == "__main__":
    main()
