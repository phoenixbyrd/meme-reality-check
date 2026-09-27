# Trending Reality Check — daily runbook (4:00 AM ET)

Run every day at 4 AM America/New_York. Today's date = the edition date.

## House rules (never break these)

- **Same rules for both sides.** A false claim from the left and a false claim from the right get the identical treatment. No partisan framing, ever.
- **Facts only.** Check each story's central claim against NAMED, published sources (e.g. Bureau of Labor Statistics, AP, Reuters, official agency releases, court filings). Never infer motive or intent. Never attribute feelings or opinions that weren't explicitly stated.
- **Attribute and admit.** State what's disputed or unknown. If a claim can't be verified either way, say so — don't guess.
- **Explain every rating.** `rating_explained` must walk through the evidence step by step: what the story asserts, what the named sources actually say (with key numbers/dates), and the explicit reasoning from evidence to verdict. A verdict without a visible evidence trail is a failed card.
- **Opinions are opinions.** Pure opinion/analysis pieces with no checkable factual claim get verdict `no-claim` ("Opinion — no checkable claim"), never a fake verdict.
- **Never fabricate.** Every `article_url` must be a real page that was opened and confirmed to match the headline. Never invent headlines, links, claims, ratings, sources, or trending context.
- The side badge ("Trending left" / "Trending right") describes where the story circulates, not whether it's true.

## Verdicts

`accurate` · `mostly-accurate` · `mixed` · `misleading` · `false` · `no-claim`

## Pipeline

### 1. Source stories (target: up to 50 left + 50 right — quality bar governs)

Spawn two research subagents in parallel (or do it directly for small runs):

- **Left:** Ground News trending, Memeorandum, Google News top stories, most-read pages at HuffPost / Daily Kos / MSNBC / MeidasTouch / Crooks and Liars, r/politics rising/hot. Search "trending political news" filtered to the last 2 days.
- **Right:** Ground News trending, Drudge Report, Memeorandum, most-read pages at Fox News / Breitbart / Daily Wire / Washington Examiner / Revolver News, r/Conservative rising/hot.

Each story must clear ALL of these:
1. Genuinely trending in the last ~48h in that side's ecosystem (most-read, most-shared, leading an aggregator — record the evidence in `trending_context`).
2. Politically newsworthy (politics, policy, governance, elections, courts — not celebrity gossip).
3. Has a central checkable factual claim.

Publish only stories that clear the bar, keeping the two sides as balanced as the day's news allows. **Never pad with filler to hit 50/50** — report the honest counts in `edition.json` `description`. If the same event trends on both sides with materially different circulating claims, it may appear once per side (each side's telling checked separately); don't list the identical article twice.

Each story needs: exact `headline`, `outlet` name, `article_url` (opened and verified), `published` date, `trending_claim` (the central assertion as it circulates, 1–2 sentences), `trending_context` (1 sentence on why it's trending on this side).

### 2. Fact-check

Split the story list across fact-check subagents (e.g. 15–20 each). Each returns, per story:
- `trending_claim` (confirm or sharpen what the story actually asserts)
- `verdict`
- `rating_explained` (3–6 sentences / 400+ characters: what the story asserts → what the named sources actually say with key numbers/dates → why this verdict follows)
- `sources` (2+ NAMED sources with real URLs that were opened — wire services, agencies, primary documents; the original article itself doesn't count as a fact-check source)

Cross-check the established fact-checkers: before finalizing a verdict, check whether Snopes, PolitiFact, FactCheck.org, Reuters Fact Check, or AP Fact Check have already rated the same claim. If they have, cite the relevant one as a corroborating source — but still verify against primary sources yourself; a fact-checker's verdict is a lead, not the evidence. If fact-checkers disagree with each other or with the primary sources, say so in `rating_explained` and let the verdict reflect the disagreement.

### 3. Assemble edition

Write `editions/<YYYY-MM-DD>/stories.json` — array of:
```json
{"id": "L01", "side": "left", "headline": "...", "outlet": "HuffPost",
 "article_url": "https://...", "published": "2026-09-27",
 "trending_claim": "...", "verdict": "mixed",
 "rating_explained": "...", "sources": [{"name": "Bureau of Labor Statistics", "url": "https://..."}],
 "trending_context": "Most-read on HuffPost; 6k shares in 24h.", "order": 1}
```
IDs: `L01`… left, `R01`… right, `order` sequential per side.

Write `editions/<YYYY-MM-DD>/edition.json`:
```json
{"kind": "stories", "title": "September 28, 2026", "date_label": "Monday, September 28, 2026",
 "description": "34 trending stories from left-leaning outlets and 31 from right-leaning outlets, each checked against the record."}
```

### 4. Validate

`python3 build.py` validates every story (required fields, verdict values, URL shape, explanation length, no metadata leakage) and **fails loudly** — a failed build means the edition is not publishable; fix the data, don't weaken the checks.

Link-check every `article_url`:
```
python3 - <<'EOF'
import json, urllib.request
for d in ["<YYYY-MM-DD>"]:
    for m in json.load(open(f"editions/{d}/stories.json")):
        req = urllib.request.Request(m["article_url"], headers={"User-Agent": "Mozilla/5.0"})
        try:
            r = urllib.request.urlopen(req, timeout=20)
            print(r.status, m["id"], m["article_url"][:80])
        except Exception as e:
            print("ERROR", m["id"], m["article_url"][:80], str(e)[:100])
EOF
```
Investigate every ERROR: a 403 from a known outlet's real URL is usually bot-blocking and acceptable (the gatherer opened it in a browser); a DNS failure, 404, or wrong-page means drop or fix the story. Never publish a "Read the original" link that doesn't resolve.

### 5. Build + deploy

```
cd ~/workspace/meme-reality-check
python3 build.py
git add -A && git commit -m "stories edition <YYYY-MM-DD>" && git push origin main
```

Then verify: `curl -s https://phoenixbyrd.github.io/meme-reality-check/editions/<YYYY-MM-DD>/ | grep -c 'class="card"'` must equal the story count. Open the page and eyeball 3–4 cards (headline links, verdict chips, explanations render).

### 6. Sanity checks before push

- Counts per side are honest; no filler.
- Verdict distribution looks honest — if all of one side is "false" and all of the other is "accurate", re-examine; real life is never that clean.
- No partisan language in `rating_explained`. No motive inference.
- No raw metadata prefixes in any text field.

## Failure handling

- If a side yields fewer than ~10 solid stories, publish what's honest and note the shortfall in `edition.json` `description`.
- If GitHub Pages shows a stale page after push, wait 2–3 minutes and re-curl.

## Notes

- `assemble.py` was the meme-era assembly helper (gather-file parsing, image downloads, text-card generation) and is **retired** — story editions are assembled directly as `stories.json`. Kept in repo for history.
- The `editions/2026-09-27-memes/` directory is the archived meme pilot; `build.py` still renders it as a legacy edition. Don't touch it.
