# Meme Reality Check — daily runbook (4:00 AM ET)

Run every day at 4 AM America/New_York. Today's date = the edition date.

## House rules (never break these)

- **Same rules for both sides.** A false claim from the left and a false claim from the right get the identical treatment. No partisan framing, ever.
- **Facts only.** Check each meme's factual claim against NAMED, published sources (e.g. Bureau of Labor Statistics, AP, Reuters, official agency releases). Never infer motive or intent. Never attribute feelings or opinions that weren't explicitly stated.
- **Attribute and admit.** State what's disputed or unknown. If a claim can't be verified either way, say so — don't guess.
- **Jokes are jokes.** Memes with no checkable factual claim get verdict `no-claim` ("Just a joke — no factual claim"), never a fake verdict.
- The side badge ("Trending left" / "Trending right") describes where the meme circulates, not whether it's true.

## Verdicts

`accurate` · `mostly-accurate` · `mixed` · `misleading` · `false` · `no-claim`

## Pipeline

### 1. Source memes (target: 50 left + 50 right)

Spawn two research subagents in parallel (or do it directly for small runs):

- **Left:** r/PoliticalHumor hot/top (old.reddit.com), left meme pages (Occupy Democrats, Being Liberal, MeidasTouch memes), left meme accounts on X. Search "trending liberal political memes this week".
- **Right:** conservative meme subreddits (verify they exist first), right meme pages on Facebook/Instagram, right meme accounts on X, and 4chan's /pol/ board (via its JSON API: `https://a.4cdn.org/pol/catalog.json` for the catalog, `https://a.4cdn.org/pol/thread/<no>.json` per thread, images at `https://i.4cdn.org/pol/<tim><ext>` — prioritize high-reply-count threads from the last day or two; skip pure shock content with no meme/claim value). Search "trending conservative political memes this week".

Each meme needs: direct `image_url`, full `meme_text` transcription, the factual `claim` (or "no checkable claim"), `source_url`, `source_name`, visible `traction` (upvotes/shares). Prioritize memes making verifiable claims. Every entry must come from a real page that was opened — never invent memes.

### 2. Download images

Save each image to `editions/<YYYY-MM-DD>/images/<ID>.jpg` (IDs: `L01`–`L50` left, `R01`–`R50` right). If a download fails, keep the meme but point `image` at the hotlink URL and note it.

### 3. Fact-check

Split the meme list across fact-check subagents (e.g. 25 each). Each returns, per meme:
`claim`, `verdict`, `reality` (2–4 plain sentences: what the checkable facts are, with numbers where relevant), `sources` (2+ named sources with URLs).

Keep `reality` tight and readable — this is shown on the card. Quote the meme's claim exactly where possible.

### 4. Assemble edition

Write `editions/<YYYY-MM-DD>/edition.json`:
```json
{"title": "September 27, 2026", "date_label": "Sunday, September 27, 2026",
 "description": "50 left-source memes and 50 right-source memes, checked against the record."}
```
Write `editions/<YYYY-MM-DD>/memes.json` — array of:
```json
{"id": "L01", "side": "left", "image": "images/L01.jpg",
 "source_name": "r/PoliticalHumor", "source_url": "https://...",
 "traction": "12.4k upvotes", "meme_text": "...", "claim": "...",
 "verdict": "false", "reality": "...",
 "sources": [{"name": "Bureau of Labor Statistics", "url": "https://..."}],
 "order": 1}
```

### 5. Build + deploy

```
cd ~/workspace/meme-reality-check
python3 build.py
git add -A && git commit -m "edition <YYYY-MM-DD>" && git push origin main
```

Then verify: `curl -s https://phoenixbyrd.github.io/meme-reality-check/editions/<YYYY-MM-DD>/ | grep -c 'class="card"'` should equal the meme count.

### 6. Sanity checks before push

- `python3 build.py` exits 0 and reports the right edition count.
- Every meme has a downloaded image OR a working hotlink (spot-check 5).
- Verdict distribution looks honest — if all 50 on one side are "false" and all 50 on the other are "accurate", re-examine; real life is never that clean.
- No partisan language in `reality` text. No motive inference.

## Failure handling

- If fewer than ~30 memes per side are findable, publish what was honestly found and note the shortfall in `edition.json` `description`. Never pad with invented memes.
- If GitHub Pages shows a stale page after push, wait 2–3 minutes and re-curl.
