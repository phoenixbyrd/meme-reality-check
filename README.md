# Meme Reality Check

A daily fact-check of trending political memes — 50 from left-leaning sources, 50 from right-leaning sources — with the actual reality behind each claim.

**Live site:** https://phoenixbyrd.github.io/meme-reality-check/

## How it works

Every day at 4:00 AM ET:
1. The most-shared political memes are collected from left-leaning sources (e.g. r/PoliticalHumor, left meme pages) and right-leaning sources (e.g. conservative meme subs/pages).
2. The factual claim inside each meme is extracted and checked against named, published sources.
3. Each meme gets a verdict: **Accurate / Mostly accurate / Mixed / Misleading / False**, or **Just a joke** when there's no checkable claim.
4. The edition is built into a static site and published here.

## Rules

- Same rules for both sides. A false claim from the left and a false claim from the right get the same treatment.
- Facts only. No partisan framing, no inferred motives. When sources disagree or something is unknown, we say so.
- The "trending left / trending right" badge says where a meme is circulating — not whether it's true.

## Repo layout

- `editions/<YYYY-MM-DD>/` — `edition.json`, `memes.json`, `images/` for each day
- `build.py` — static site generator → `docs/` (GitHub Pages)
- `WORKFLOW.md` — the daily runbook the 4 AM job follows
