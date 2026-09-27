#!/usr/bin/env python3
"""Trending Reality Check static site generator.

Reads editions/<YYYY-MM-DD>/edition.json + stories.json (or memes.json
for the legacy 2026-09-27-memes pilot edition), writes a modern static
site into docs/ ready for GitHub Pages.

- / : latest edition (card grid with side/verdict filters)
- /editions/<date>/ : that day's edition
- /archive.html : past editions

stories.json entry:
  {id, side ("left"|"right"), headline, outlet, article_url, published,
   trending_claim, verdict, rating_explained, sources:[{name,url}],
   trending_context, order}
verdict: accurate | mostly-accurate | mixed | misleading | false | no-claim
"""
import json
import os
import re
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


def fail(msg):
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


VERDICTS = {
    "accurate":        ("Accurate", "#22c55e"),
    "mostly-accurate": ("Mostly accurate", "#a3e635"),
    "mixed":           ("Mixed", "#fbbf24"),
    "misleading":      ("Misleading", "#fb923c"),
    "false":           ("False", "#ef4444"),
    "no-claim":        ("Opinion — no checkable claim", "#9ca3af"),
}
VERDICT_ORDER = ["accurate", "mostly-accurate", "mixed", "misleading", "false", "no-claim"]

STORY_REQUIRED = ["id", "side", "headline", "outlet", "article_url",
                  "trending_claim", "verdict", "rating_explained", "sources"]


def validate_stories(stories, date):
    seen = set()
    for m in stories:
        mid = m.get("id", "?")
        for f in STORY_REQUIRED:
            if not m.get(f):
                fail(f"{date} {mid}: missing/empty required field '{f}'")
        if m["side"] not in ("left", "right"):
            fail(f"{date} {mid}: bad side '{m['side']}'")
        if m["verdict"] not in VERDICTS:
            fail(f"{date} {mid}: bad verdict '{m['verdict']}'")
        if mid in seen:
            fail(f"{date} {mid}: duplicate id")
        seen.add(mid)
        if not re.match(r"https?://", m["article_url"]):
            fail(f"{date} {mid}: article_url is not a URL: {m['article_url']!r}")
        if len(m["rating_explained"]) < 100:
            fail(f"{date} {mid}: rating_explained too short "
                 f"({len(m['rating_explained'])} chars) — explanations must walk through the evidence")
        if not isinstance(m["sources"], list) or len(m["sources"]) < 1:
            fail(f"{date} {mid}: need at least 1 named source")
        for s in m["sources"]:
            if not s.get("name"):
                fail(f"{date} {mid}: source missing name")
        for f in ("trending_claim", "rating_explained", "headline"):
            if "CHECKABLE" in str(m.get(f, "")):
                fail(f"{date} {mid}: raw metadata leaked into '{f}'")


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0f14;--card:#161a23;--card2:#1d2230;--line:#262c3d;--txt:#e8ebf2;--mut:#9aa3b8;--acc:#7c5cff}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--txt);line-height:1.6;min-height:100vh}
a{color:#8ea6ff;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.site{background:rgba(13,15,20,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:50;transition:transform .28s ease}
header.site.hide{transform:translateY(-110%)}
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
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px;padding:26px 0 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,border-color .15s}
.card:hover{transform:translateY(-3px);border-color:#3a4360}
.card.hidden{display:none}
.memeimg{width:100%;aspect-ratio:1/1;object-fit:cover;background:#0a0c10;cursor:zoom-in;display:block}
.card .body{padding:18px 20px 20px;display:flex;flex-direction:column;gap:10px;flex:1}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.side{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border-radius:999px;padding:4px 11px}
.side.left{background:rgba(96,165,250,.14);color:#7fb3ff;border:1px solid rgba(96,165,250,.4)}
.side.right{background:rgba(248,113,113,.13);color:#ff9d9d;border:1px solid rgba(248,113,113,.4)}
.verdict{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border-radius:999px;padding:4px 11px;border:1px solid}
.headline{font-size:19px;font-weight:700;line-height:1.35;color:#fff}
a.headline:hover{color:#8ea6ff;text-decoration:none}
.byline{font-size:12px;color:var(--mut)}
.byline .read{font-weight:600}
.claim{font-size:14px;color:var(--mut);font-style:italic;border-left:3px solid var(--line);padding-left:12px}
.claim b{color:var(--txt);font-style:normal;display:block;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.reality{font-size:14px;color:var(--txt)}
.reality b{display:block;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--mut);margin-bottom:4px}
.srcs{font-size:12px;color:var(--mut);margin-top:auto;padding-top:8px;border-top:1px dashed var(--line)}
.srcs a{margin-right:10px}
.trsrc{font-size:12px;color:var(--mut)}
.trsrc a{color:var(--mut);text-decoration:underline}
.whytrend{font-size:12px;color:var(--mut);font-style:italic}
.how{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin:10px 0 40px;font-size:14px;color:var(--mut)}
.how h2{color:#fff;font-size:18px;margin-bottom:10px}
.how li{margin:6px 0 6px 18px}
footer.site{border-top:1px solid var(--line);padding:26px 0;margin-top:10px;font-size:13px;color:var(--mut)}
.archive-list{list-style:none;padding:24px 0 40px}
.archive-list li{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 22px;margin-bottom:12px}
.archive-list .d{font-size:13px;color:var(--mut)}
.archive-list .kindtag{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--acc);border:1px solid var(--acc);border-radius:999px;padding:2px 10px;margin-left:8px;vertical-align:middle}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;align-items:center;justify-content:center;z-index:100;cursor:zoom-out;padding:24px}
.lightbox.open{display:flex}
.lightbox img{max-width:100%;max-height:100%;border-radius:12px}
.ednav{display:flex;justify-content:space-between;padding:8px 0 30px;font-size:14px}
.dateline{font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--mut);text-align:center;margin-top:26px}
/* ---- hamburger drawer menu ---- */
#menuBtn{position:fixed;top:14px;right:14px;z-index:100;width:46px;height:46px;border-radius:12px;background:rgba(20,24,33,.94);border:1px solid var(--line);cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px}
#menuBtn span{display:block;width:20px;height:2px;background:#fff;border-radius:2px;transition:transform .25s ease,opacity .25s ease}
#menuBtn.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
#menuBtn.open span:nth-child(2){opacity:0}
#menuBtn.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
#scrim{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:90;opacity:0;pointer-events:none;transition:opacity .25s ease}
#scrim.show{opacity:1;pointer-events:auto}
#drawer{position:fixed;top:0;right:0;bottom:0;width:min(320px,84vw);background:#10141c;border-left:1px solid var(--line);z-index:95;transform:translateX(105%);transition:transform .3s ease;overflow-y:auto;padding:76px 20px 30px}
#drawer.open{transform:none}
.d-sec{margin-bottom:26px}
.d-h{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--mut);margin-bottom:10px}
.d-sec>a{display:block;color:var(--txt);padding:11px 2px;border-bottom:1px solid var(--line);font-size:15px}
.d-btns{display:flex;flex-wrap:wrap;gap:8px}
.d-foot{font-size:13px;color:var(--mut)}
/* ---- news layout (story editions) ---- */
.nameplate{text-align:center;padding:34px 0 16px;border-bottom:3px double var(--line);margin-bottom:6px}
.np-kicker{font-size:11px;text-transform:uppercase;letter-spacing:3px;color:var(--acc)}
.np-title{font-family:Georgia,'Times New Roman',serif;font-size:clamp(36px,6vw,60px);font-weight:800;color:#fff;margin:8px 0 6px}
.np-title .vs{color:#ff5c7a;font-style:italic;font-weight:400}
.np-tag{color:var(--mut);font-size:14px;max-width:640px;margin:0 auto}
.np-meta{font-size:12px;color:var(--mut);margin-top:10px}
.scoreboard{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;padding:14px 0 4px}
.sb{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 14px;font-size:12px;color:var(--mut)}
.sb b{color:#fff;margin-right:6px}
.leadstory{border-bottom:1px solid var(--line);padding:22px 0 26px;margin-bottom:8px}
.leadstory.hidden{display:none}
.leadstory .kicker{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--acc);margin-bottom:8px}
.lead-head{font-family:Georgia,serif;font-size:clamp(26px,4vw,40px);font-weight:800;color:#fff;line-height:1.2}
a.lead-head:hover{color:#8ea6ff;text-decoration:none}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:34px;padding:10px 0 30px}
@media(max-width:860px){.cols{grid-template-columns:1fr}}
.sidecol h2{font-family:Georgia,serif;font-size:22px;color:#fff;padding-bottom:10px;border-bottom:2px solid var(--line);margin-bottom:4px;display:flex;align-items:center;gap:10px}
.sidecol h2 .count{font-size:12px;color:var(--mut);font-weight:400;margin-left:auto;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:none}
.dot.left{background:#60a5fa}.dot.right{background:#f87171}
.brief{padding:16px 0;border-bottom:1px solid var(--line)}
.brief.hidden{display:none}
.b-head{font-family:Georgia,serif;font-size:18px;font-weight:700;color:#fff;line-height:1.35}
a.b-head:hover{color:#8ea6ff;text-decoration:none}
.b-meta{font-size:12px;color:var(--mut);margin:6px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.b-claim{font-size:13.5px;color:var(--mut);font-style:italic;margin:6px 0}
.b-claim b,.b-why b{color:var(--txt);font-style:normal}
.b-why{font-size:13.5px;color:var(--txt);margin:6px 0}
.b-src{font-size:12px;color:var(--mut)}
.b-src a{margin-right:8px}
"""


JS = """
(function(){
const fsrc=document.getElementById('filterSrc');
const dS=document.getElementById('dSide'),dV=document.getElementById('dVerdict');
if(fsrc&&dS&&dV){
fsrc.querySelectorAll('.fbtn[data-side]').forEach(b=>dS.appendChild(b));
fsrc.querySelectorAll('.fbtn[data-verdict]').forEach(b=>dV.appendChild(b));
const fc0=document.getElementById('fcount');
if(fc0)document.querySelector('.d-foot').appendChild(fc0);
fsrc.remove();
}
[dS,dV].forEach(d=>{if(d&&!d.children.length)d.closest('.d-sec').style.display='none';});
const menuBtn=document.getElementById('menuBtn'),drawer=document.getElementById('drawer'),scrim=document.getElementById('scrim');
function setMenu(open){menuBtn.classList.toggle('open',open);drawer.classList.toggle('open',open);scrim.classList.toggle('show',open);}
menuBtn.onclick=()=>setMenu(!drawer.classList.contains('open'));
scrim.onclick=()=>setMenu(false);
drawer.querySelectorAll('a').forEach(a=>a.onclick=()=>setMenu(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMenu(false);});
})();
const sideBtns=[...document.querySelectorAll('.fbtn[data-side]')];
const verBtns=[...document.querySelectorAll('.fbtn[data-verdict]')];
let side='all',verdict='all';
function apply(){
  let n=0;
  document.querySelectorAll('.card,.brief[data-side],.leadstory[data-side]').forEach(c=>{
    const okS=side==='all'||c.dataset.side===side;
    const okV=verdict==='all'||c.dataset.verdict===verdict;
    const show=okS&&okV;
    c.classList.toggle('hidden',!show);
    if(show)n++;
  });
  const fce=document.getElementById('fcount');if(fce)fce.textContent=n+' shown';
}
sideBtns.forEach(b=>b.onclick=()=>{side=b.dataset.side;sideBtns.forEach(x=>x.classList.toggle('on',x===b));apply();});
verBtns.forEach(b=>b.onclick=()=>{verdict=b.dataset.verdict;verBtns.forEach(x=>x.classList.toggle('on',x===b));apply();});
const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.querySelectorAll('.memeimg').forEach(im=>im.onclick=()=>{lbi.src=im.src;lb.classList.add('open');});
if(lb)lb.onclick=()=>lb.classList.remove('open');
document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.classList.remove('open');});
apply();
let lastY=window.scrollY;const hdr=document.querySelector('header.site');
window.addEventListener('scroll',()=>{const y=window.scrollY;
if(y>lastY+4&&y>140){hdr.classList.add('hide');document.body.classList.add('navhidden');}
else if(y<lastY-4){hdr.classList.remove('hide');document.body.classList.remove('navhidden');}
lastY=y;},{passive:true});
"""

PAGE_TOP = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Trending Reality Check</title>
<meta name="description" content="Daily fact-check of top trending political stories from left- and right-leaning outlets. What's trending vs. what's true.">
<style>""" + CSS + """</style></head>
<body>
"""

HEADER = """<header class="site"><div class="wrap">
<div><a class="brand" href="{base}/"><span class="m1">TRENDING</span> <span class="m2">VS</span> <span class="m1">REALITY</span></a><div class="tagline">What's trending vs. what's true.</div></div>
</div></header>
<button id="menuBtn" aria-label="Open menu"><span></span><span></span><span></span></button>
<div id="scrim"></div>
<aside id="drawer" aria-label="Site menu">
<div class="d-sec"><div class="d-h">Menu</div>
<a href="{base}/">Today's edition</a>
<a href="{base}/archive.html">Archive</a>
<a href="#how">How we rate</a>
</div>
<div class="d-sec"><div class="d-h">Side</div><div class="d-btns" id="dSide"></div></div>
<div class="d-sec"><div class="d-h">Verdict</div><div class="d-btns" id="dVerdict"></div></div>
<div class="d-foot"></div>
</aside>"""

FOOTER = """<footer class="site"><div class="wrap">
<strong style="color:#fff">Trending Reality Check</strong> — every day we pull the top trending political stories from left-leaning and right-leaning outlets, link the originals, and check the central claims against named sources. Same rules for both sides.<br>
<span style="font-size:12px">Articles belong to their publishers and are linked for reference. The September 27, 2026 meme pilot edition is preserved in the archive. Corrections: reply in the Muse app.</span>
</div></footer>
<div class="lightbox" id="lb"><img id="lbi" alt="image enlarged"></div>
<script>""" + JS + """</script>
</body></html>"""

HOW_STORIES = """<div class="how" id="how"><h2>How we rate</h2>
<ul>
<li><strong style="color:#fff">Where the stories come from.</strong> Each day we collect the most-trending political stories from left-leaning outlets and right-leaning outlets. The "trending left / trending right" badge says where a story is circulating — not whether it's true.</li>
<li><strong style="color:#fff">What we check.</strong> We pull out the central factual claim in each story and check it against named, published sources. "Why this rating" walks through the evidence step by step. Pure opinion pieces with no checkable claim get "Opinion — no checkable claim" instead of a fake verdict.</li>
<li><strong style="color:#fff">Same rules for both sides.</strong> A false claim from the left and a false claim from the right get the same treatment. We don't infer motives, we don't do partisan framing, and when sources disagree or something is unknown, we say so.</li>
<li><strong style="color:#fff">Read the original.</strong> Every card links the original article so you can check our work.</li>
</ul></div>"""

HOW_MEMES = """<div class="how" id="how"><h2>How we rated (pilot meme edition)</h2>
<ul>
<li><strong style="color:#fff">Where the memes came from.</strong> The most-shared political memes from left-leaning sources and right-leaning sources. The "trending left / trending right" badge said where a meme circulated — not whether it was true.</li>
<li><strong style="color:#fff">What we checked.</strong> The factual claim inside each meme, checked against named, published sources. Pure jokes got "Just a joke — no factual claim" instead of a fake verdict.</li>
<li><strong style="color:#fff">Same rules for both sides.</strong> No motive inference, no partisan framing; disputed or unknown points were stated as such.</li>
</ul></div>"""


def verdict_chip(v):
    label, color = VERDICTS.get(v, VERDICTS["no-claim"])
    return (f'<span class="verdict" style="color:{color};border-color:{color}55;'
            f'background:{color}14">&#9679; {esc(label)}</span>')


def side_badge(side):
    if side == "left":
        return '<span class="side left">Trending left</span>'
    return '<span class="side right">Trending right</span>'


SEVERITY = {"false": 0, "misleading": 1, "mixed": 2,
            "mostly-accurate": 3, "accurate": 4, "no-claim": 5}


def brief_sources(m):
    return " ".join(
        f'<a href="{esc(s.get("url", "#"))}" target="_blank" rel="noopener">{esc(s.get("name", "source"))}</a>'
        for s in m.get("sources", []))


def brief_html(m):
    vlabel = VERDICTS.get(m.get("verdict"), VERDICTS["no-claim"])[0]
    srcs = brief_sources(m)
    pub = f" &middot; {esc(m['published'])}" if m.get("published") else ""
    claim = m.get("trending_claim") or "No checkable factual claim — opinion or analysis."
    return f"""<article class="brief" data-side="{m['side']}" data-verdict="{m['verdict']}">
<a class="b-head" href="{esc(m['article_url'])}" target="_blank" rel="noopener">{esc(m['headline'])}</a>
<div class="b-meta"><span>{esc(m['outlet'])}{pub}</span>{verdict_chip(m['verdict'])}<a href="{esc(m['article_url'])}" target="_blank" rel="noopener">Read the original &rarr;</a></div>
<p class="b-claim"><b>The claim:</b> {esc(claim)}</p>
<p class="b-why"><b>Why {esc(vlabel.lower())}:</b> {esc(m.get('rating_explained', ''))}</p>
<div class="b-src"><strong>Sources:</strong> {srcs if srcs else "&mdash;"}</div>
</article>"""


def lead_html(m):
    vlabel = VERDICTS.get(m.get("verdict"), VERDICTS["no-claim"])[0]
    srcs = brief_sources(m)
    pub = f" &middot; {esc(m['published'])}" if m.get("published") else ""
    side_word = "the left" if m["side"] == "left" else "the right"
    return f"""<section class="leadstory" data-side="{m['side']}" data-verdict="{m['verdict']}">
<div class="kicker">Top reality check &middot; trending on {side_word}</div>
<a class="lead-head" href="{esc(m['article_url'])}" target="_blank" rel="noopener">{esc(m['headline'])}</a>
<div class="b-meta"><span>{esc(m['outlet'])}{pub}</span>{verdict_chip(m['verdict'])}<a href="{esc(m['article_url'])}" target="_blank" rel="noopener">Read the original &rarr;</a></div>
<p class="b-claim"><b>The claim:</b> {esc(m.get('trending_claim') or 'No checkable factual claim — opinion or analysis.')}</p>
<p class="b-why"><b>Why {esc(vlabel.lower())}:</b> {esc(m.get('rating_explained', ''))}</p>
<div class="b-src"><strong>Sources:</strong> {srcs if srcs else "&mdash;"}</div>
</section>"""


def pick_lead(items, date):
    # most severe verdict leads; ties alternate sides by day for fairness
    try:
        daynum = int(str(date)[8:10])
    except Exception:
        daynum = 1
    first_side = "left" if daynum % 2 == 1 else "right"
    return sorted(items, key=lambda m: (SEVERITY.get(m.get("verdict", "no-claim"), 5),
                                        0 if m["side"] == first_side else 1,
                                        m.get("order", 0)))[0]


def edition_page_stories(date, edition, items, prev_date, next_date):
    sev = lambda m: (SEVERITY.get(m.get("verdict", "no-claim"), 5), m.get("order", 0))
    left = sorted([m for m in items if m["side"] == "left"], key=sev)
    right = sorted([m for m in items if m["side"] == "right"], key=sev)
    lead = pick_lead(items, date)
    left = [m for m in left if m["id"] != lead["id"]]
    right = [m for m in right if m["id"] != lead["id"]]
    counts = {v: 0 for v in VERDICTS}
    for m in items:
        counts[m.get("verdict", "no-claim")] = counts.get(m.get("verdict", "no-claim"), 0) + 1
    left_n = sum(1 for m in items if m["side"] == "left")
    right_n = sum(1 for m in items if m["side"] == "right")
    sb = ('<div class="scoreboard"><span class="sb"><b>' + str(left_n) + '</b>trending left</span>'
          f'<span class="sb"><b>{right_n}</b>trending right</span>' +
          "".join(f'<span class="sb"><b style="color:{VERDICTS[v][1]}">{counts[v]}</b>{VERDICTS[v][0]}</span>'
                  for v in VERDICT_ORDER if counts[v]) + '</div>')
    ver_btns = "".join(f'<button class="fbtn" data-verdict="{v}">{VERDICTS[v][0]}</button>'
                       for v in VERDICT_ORDER)
    nav = []
    if prev_date:
        nav.append(f'<a href="{BASE_URL}/editions/{prev_date}/">&larr; {prev_date}</a>')
    else:
        nav.append('<span></span>')
    if next_date:
        nav.append(f'<a href="{BASE_URL}/editions/{next_date}/">{next_date} &rarr;</a>')
    else:
        nav.append(f'<a href="{BASE_URL}/archive.html">Archive &rarr;</a>')
    left_html = "\n".join(brief_html(m) for m in left)
    right_html = "\n".join(brief_html(m) for m in right)
    return (PAGE_TOP.replace("{title}", edition["title"]) + HEADER.replace("{base}", BASE_URL) + f"""
<div class="wrap">
<div class="nameplate">
<div class="np-kicker">Daily story fact-check</div>
<div class="np-title">Trending <span class="vs">vs.</span> Reality</div>
<div class="np-tag">What's trending vs. what's true — every claim checked against named sources, same standard for both sides.</div>
<div class="np-meta">{esc(edition['date_label'])} &middot; Daily edition</div>
</div>
{sb}
<div id="filterSrc" hidden>
<button class="fbtn on" data-side="all">All</button>
<button class="fbtn" data-side="left">Left</button>
<button class="fbtn" data-side="right">Right</button>
<button class="fbtn on" data-verdict="all">Any verdict</button>
{ver_btns}
<span class="fcount" id="fcount"></span>
</div>
{lead_html(lead)}
<div class="cols">
<section class="sidecol"><h2><span class="dot left"></span>Trending on the Left<span class="count">{left_n} stories</span></h2>
{left_html}</section>
<section class="sidecol"><h2><span class="dot right"></span>Trending on the Right<span class="count">{right_n} stories</span></h2>
{right_html}</section>
</div>
{HOW_STORIES}
<div class="ednav">{nav[0]}{nav[1]}</div>
</div>
{FOOTER}""")


def edition_page(date, edition, items, prev_date, next_date):
    if edition.get("kind", "stories") == "stories":
        return edition_page_stories(date, edition, items, prev_date, next_date)
    return edition_page_memes(date, edition, items, prev_date, next_date)


def meme_card(m, date):
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


def edition_page_memes(date, edition, items, prev_date, next_date):
    kind = edition.get("kind", "stories")
    is_stories = kind == "stories"
    cards = "\n".join(meme_card(m, date) for m in sorted(items, key=lambda x: x.get("order", 0)))
    counts = {v: 0 for v in VERDICTS}
    for m in items:
        counts[m.get("verdict", "no-claim")] = counts.get(m.get("verdict", "no-claim"), 0) + 1
    left_n = sum(1 for m in items if m["side"] == "left")
    right_n = sum(1 for m in items if m["side"] == "right")
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
        nav.append(f'<a href="{BASE_URL}/editions/{next_date}/">{next_date} &rarr;</a>')
    else:
        nav.append(f'<a href="{BASE_URL}/archive.html">Archive &rarr;</a>')
    kicker, h1, side_l, side_r = (
        "Meme pilot edition",
        'The memes, <span class="grad">minus the spin.</span>',
        "from left-leaning sources", "from right-leaning sources")
    how = HOW_MEMES
    return (PAGE_TOP.replace("{title}", edition["title"]) + HEADER.replace("{base}", BASE_URL) + f"""
<div class="wrap">
<div class="dateline">{esc(edition['date_label'])} &middot; Daily edition</div>
<div class="hero">
<span class="kicker">{kicker}</span>
<h1>{h1}</h1>
<p>{esc(edition['description'])}</p>
<div class="stats">
<div class="stat"><b>{left_n}</b>{side_l}</div>
<div class="stat"><b>{right_n}</b>{side_r}</div>
{stat_cells}
</div>
</div>
</div>
<div id="filterSrc" hidden>
<button class="fbtn on" data-side="all">All</button>
<button class="fbtn" data-side="left">Trending left</button>
<button class="fbtn" data-side="right">Trending right</button>
<button class="fbtn on" data-verdict="all">Any verdict</button>
{ver_btns}
<span class="fcount" id="fcount"></span>
</div>
<div class="wrap">
<div class="grid">{cards}</div>
{how}
<div class="ednav">{nav[0]}{nav[1]}</div>
</div>
{FOOTER}""")


def archive_label(edition):
    kind = edition.get("kind", "stories")
    ln, rn = edition.get("left_n", 0), edition.get("right_n", 0)
    tag = '<span class="kindtag">stories</span>' if kind == "stories" else '<span class="kindtag">meme pilot</span>'
    noun = "stories" if kind == "stories" else "memes"
    return (f"{ln} left-leaning {noun}, {rn} right-leaning {noun}", tag)


def archive_page(items):
    lis = ""
    for d, ed in items:
        desc, tag = archive_label(ed)
        lis += f"""<li><a href="{BASE_URL}/editions/{d}/"><strong style="color:#fff">{esc(ed['title'])}</strong></a>{tag}
<div class="d">{esc(ed['date_label'])} &middot; {desc} checked</div></li>"""
    return (PAGE_TOP.replace("{title}", "Archive") + HEADER.replace("{base}", BASE_URL) + f"""
<div class="wrap">
<div class="dateline">Archive</div>
<div class="hero"><h1>Past <span class="grad">editions.</span></h1></div>
<ul class="archive-list">{lis}</ul>
</div>
{FOOTER}""")


def edition_key(d):
    # plain YYYY-MM-DD dirs sort as the day's main edition; suffixed
    # dirs (e.g. 2026-09-27-memes) are earlier revisions of the same day
    base = d[:10]
    plain = 1 if d == base else 0
    return (base, plain)


def load_edition(d):
    edir = os.path.join(EDITIONS, d)
    with open(os.path.join(edir, "edition.json")) as f:
        edition = json.load(f)
    sp = os.path.join(edir, "stories.json")
    mp = os.path.join(edir, "memes.json")
    if os.path.exists(sp):
        with open(sp) as f:
            items = json.load(f)
        validate_stories(items, d)
        kind = "stories"
    elif os.path.exists(mp):
        with open(mp) as f:
            items = json.load(f)
        kind = "memes"
    else:
        fail(f"{d}: neither stories.json nor memes.json found")
    edition.setdefault("kind", kind)
    return edition, items


def main():
    dates = sorted([d for d in os.listdir(EDITIONS)
                    if re.match(r"^\d{4}-\d{2}-\d{2}", d)
                    and os.path.isdir(os.path.join(EDITIONS, d))
                    and os.path.exists(os.path.join(EDITIONS, d, "edition.json"))],
                   key=edition_key, reverse=True)
    if not dates:
        print("no editions", file=sys.stderr)
        sys.exit(1)
    os.makedirs(SITE, exist_ok=True)

    editions = {}
    for d in dates:
        edition, items = load_edition(d)
        editions[d] = (edition, items)
        # copy images (legacy meme editions only)
        src_img = os.path.join(EDITIONS, d, "images")
        dst_img = os.path.join(SITE, "editions", d, "images")
        if os.path.isdir(src_img):
            for fn in os.listdir(src_img):
                os.makedirs(dst_img, exist_ok=True)
                shutil.copy2(os.path.join(src_img, fn), os.path.join(dst_img, fn))
        edition["left_n"] = sum(1 for m in items if m["side"] == "left")
        edition["right_n"] = sum(1 for m in items if m["side"] == "right")

    for i, d in enumerate(dates):
        edition, items = editions[d]
        prev_d = dates[i + 1] if i + 1 < len(dates) else None
        next_d = dates[i - 1] if i - 1 >= 0 else None
        out_dir = os.path.join(SITE, "editions", d)
        os.makedirs(out_dir, exist_ok=True)
        html = edition_page(d, edition, items, prev_d, next_d)
        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write(html)
        if i == 0:  # latest edition is also the homepage
            with open(os.path.join(SITE, "index.html"), "w") as f:
                f.write(html)

    with open(os.path.join(SITE, "archive.html"), "w") as f:
        f.write(archive_page([(d, editions[d][0]) for d in dates]))
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    total = sum(len(v[1]) for v in editions.values())
    print(f"built {len(dates)} edition(s): {', '.join(dates)} ({total} cards)")


if __name__ == "__main__":
    main()
