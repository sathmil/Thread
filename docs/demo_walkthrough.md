# Demo Walkthrough

## One-sentence pitch

Thread turns a collection of personal narratives into something explorable — a story map to wander, a mirror to see
yourself in, and a conversational layer to ask it questions — built on real vector search, versioned embeddings, and
an evaluation dashboard that treats retrieval quality as a first-class metric, not an afterthought.

## Setup

```bash
docker compose up -d db redis
cd backend && source ../myenv/bin/activate
alembic upgrade head
python -m scripts.seed                 # seeds the public 10-story demo dataset
uvicorn app.main:app --port 8000       # backend, terminal 1
celery -A app.celery_app worker --pool=solo   # worker, terminal 2 (macOS: --pool=solo, see README)
cd ../frontend && npm run dev          # frontend, terminal 3
```

Open `http://localhost:3000`.

## Demo flow

1. **Explore** (the homepage) — hover a point to preview a story, click one to open it, double-click one to
   highlight its nearest neighbors, then type `belonging` into the search box and watch matching points highlight
   live. Try zoom in / zoom out and the pan arrows to split apart a dense theme.
2. **A story page** (`/stories/[id]`, reached by clicking any point or table row) — read the theme it belongs to,
   its Journey (nearest stories and *why*, plus one deliberately contrasting story), its reflection questions, then
   toggle "curious? see the raw signal" to reveal the fingerprint chart underneath.
3. **Mirror** (`/mirror`) — paste a few sentences of your own experience and submit. No account needed. Watch it
   return specific, real matches with grounded explanations and your own fingerprint chart — this works with zero
   API keys configured.
4. **Ask** (`/ask`) — try "what themes usually appear alongside belonging?" With an `OPENAI_API_KEY` configured, the
   agent calls real tools (search, theme lookup, story comparison) and answers in plain language, showing which
   tools it used. Without a key, it shows the honest "not configured" message rather than failing silently.
5. **Themes** (`/clusters`) — theme cards, each with a summary labeled "AI-written" or "Auto-generated" depending on
   whether an LLM key was available, plus its member stories.
6. **Insights** (`/insights`) — real, reproducible findings: correlations across narrative dimensions (e.g. "stories
   high on belonging are also high on agency, r=0.91") and standout stories (most representative per theme, most
   unique in the corpus, most emotionally complex).
7. **Search** (`/search`) — classic semantic search, switch the unit between Sentences/Passages/Stories to show
   retrieval granularity.
8. **Evaluation** (`/evaluation`) — run the gold-query suite, switch the embedding model, watch Recall@K/MRR/
   Precision@K and the score distribution update, then open History and click an older run to load its full
   breakdown — this is where MiniLM vs. OpenAI or pre/post-reindex comparisons live.
9. **Workspace** (`/workspace`, requires Clerk configured) — sign in, create a private dataset, upload a CSV with a
   `story_text` column, index it, and watch the job progress bar (async above 25 stories).
10. **Dataset** (`/dataset`) — the raw story table with enriched metadata.

## API demo (no frontend required)

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "finding my voice", "unit": "Passages", "top_k": 5}'
curl -s -X POST http://localhost:8000/mirror \
  -H "Content-Type: application/json" \
  -d '{"story_text": "I moved every year and never felt like I belonged, until I found a small group of people who felt like family."}'
curl -s "http://localhost:8000/evaluation/run?unit=Passages&top_k=3"
```

Full route reference: `docs/api.md`. Swagger UI at `/docs` while the backend is running.

## Screenshot checklist

- The Explore map, mid-hover on a point (tooltip visible)
- A story page with the Journey section and an open fingerprint chart
- Mirror my story, showing real matches for a pasted paragraph
- Ask, showing tool-call transparency (or the honest fallback message)
- Themes, showing an "AI-written" summary badge
- Insights, showing at least one correlation and one standout story
- Evaluation, showing the History table with more than one run

## Framing for a technical audience

This project is two things built in deliberate order: first, genuine production infrastructure (versioned
embeddings, idempotent background indexing, real vector search, CI against a real database), then a product layer
that only makes sense once that infrastructure exists (Journey explanations grounded in real fingerprint deltas, an
insight engine that never lets an LLM invent a statistic, a conversational agent that's provably incapable of doing
anything the rest of the app can't already do). The throughline across both halves: nothing in the "AI" layer is
allowed to assert something that wasn't actually computed — every fluent sentence in this app is phrasing a real
number, not replacing one.
