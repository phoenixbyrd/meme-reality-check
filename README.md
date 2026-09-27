# Trending Reality Check

A daily fact-check of the top trending political stories — from left-leaning outlets and right-leaning outlets — with the actual reality behind each claim.

**Live site:** https://phoenixbyrd.github.io/meme-reality-check/

## How it works

Every day at 4:00 AM ET:
1. The most-trending political stories are collected from left-leaning outlets and right-leaning outlets (up to 50 per side; only stories that clear the trending + newsworthy + checkable bar are published — never padded).
2. The central factual claim in each story is extracted and checked against named, published sources.
3. Each story gets a verdict — **Accurate / Mostly accurate / Mixed / Misleading / False**, or **Opinion — no checkable claim** — plus a full explanation walking through the evidence behind the rating.
4. Every card links the original article so readers can check the work.
5. The edition is built into a static site and published here.

## Rules

- Same rules for both sides. A false claim from the left and a false claim from the right get the same treatment.
- Facts only. No partisan framing, no inferred motives. When sources disagree or something is unknown, we say so.
- The "trending left / trending right" badge says where a story is circulating — not whether it's true.
- Nothing is fabricated: every article link is opened and verified, every source is named.

## Repo layout

- `editions/<YYYY-MM-DD>/` — `edition.json`, `stories.json` for each day
- `editions/2026-09-27-memes/` — the archived meme pilot edition (legacy format, still rendered)
- `build.py` — static site generator → `docs/` (GitHub Pages); validates every story and fails loudly on bad data
- `WORKFLOW.md` — the daily runbook the 4 AM job follows

## History

Launched September 27, 2026 as "Meme Reality Check" (50/50 political meme fact-check). Pivoted the same day to trending-story fact-checks with original-article links and full rating explanations, keeping the 50/50 left/right structure and the same-evidence-for-both-sides rule.
