# API Reference

Base URL (local dev): `http://localhost:8000`. All request/response bodies are JSON unless noted. Interactive docs
are also available at `/docs` (Swagger UI) whenever the backend is running.

## Auth

Send `Authorization: Bearer <Clerk JWT>` for authenticated requests. Every route accepts requests with **no** token —
`get_current_user` resolves to `None` rather than rejecting the request, so public datasets and read-only routes work
fully signed-out. Only routes that mutate a specific dataset (`require_user`, plus an ownership check) require a
token. See `docs/security.md` for the full model.

| Outcome | When |
|---|---|
| `401` | The route requires sign-in (`require_user`) and no/invalid token was sent. |
| `403` | A token was sent, but that user doesn't own the private dataset being accessed/modified. |
| `404` | The resource (dataset, story, job, run) doesn't exist. |

## Health

`GET /health` → `{ status, db_ok }`. No auth.

## Datasets

| Route | Auth | Notes |
|---|---|---|
| `GET /datasets` | optional | Public datasets, plus the caller's own private ones if signed in. |
| `POST /datasets` | required | Creates a private dataset owned by the caller. |
| `GET /datasets/{id}` | scoped | 401/403 per the table above for private datasets. |
| `POST /datasets/{id}/upload` | owner | Multipart CSV upload; requires a `story_text` column, `id` optional (auto-generated and zero-padded if missing). |
| `POST /datasets/{id}/index` | owner | Body: `{ embedding_model }` (`"Local MiniLM"` default or `"OpenAI API"`). Chunks, embeds, and clusters. Sync under 25 stories, otherwise dispatched to Celery — see `docs/scaling.md`. Returns a `Job`. |
| `POST /datasets/{id}/reindex` | owner | Same shape as `/index`, but for re-embedding an already-indexed dataset under a different model without deleting the old embeddings. |

## Jobs

`GET /jobs/{id}` (scoped to the job's dataset) → status/progress polling target for `/index` and `/reindex`.
`status` is one of `queued|running|succeeded|failed`; `warning_message` is set when a requested provider silently
fell back (e.g. `"OpenAI API"` requested with no `OPENAI_API_KEY` configured).

## Stories

| Route | Auth | Notes |
|---|---|---|
| `GET /stories` | scoped (defaults to the public seed dataset if `dataset_id` omitted) | List view for the Dataset table. |
| `GET /stories/{id}` | scoped | Full story text + its theme name. |
| `GET /stories/{id}/fingerprint` | scoped | Computes-and-caches on first request (see `docs/database_schema.md`, `story_fingerprints`). |
| `GET /stories/{id}/journey?top_k=3` | scoped | Nearest neighbors, a farthest "contrasting" story, "why similar" explanations, and reflection questions. |

## Search

`POST /search` — body: `{ query, unit, top_k, embedding_model?, dataset_id? }` (`unit` is one of
`Sentences|Passages|Stories`). Embeds the query and ranks by pgvector cosine distance, scoped to
`dataset_id` (defaults to the public seed dataset).

## Themes (clusters)

| Route | Notes |
|---|---|
| `GET /clusters?dataset_id=&embedding_model=` | Theme cards: label, summary (`summary_source: rule_based\|llm`), member stories. |
| `GET /clusters/projection?dataset_id=&embedding_model=` | 2D PCA coordinates for the map (`x`, `y`, theme, preview). |

## Insights

`GET /datasets/{id}/insights?embedding_model=` — computes-and-caches per `(dataset, embedding_model)` on first
request. Each finding has a `finding_type` (`correlation`, `most_representative`, `most_unique`, `most_complex`,
`theme_bridge`, `theme_migration`), grounded numbers (`effect_size`, `sample_size`), and an optional subject story.

## Conversational query

`POST /query` — body: `{ question, dataset_id? }`. Response: `{ available, answer, tool_calls[] }`.
`available: false` when no `OPENAI_API_KEY` is configured — `answer` is then a plain "not configured" message and
`tool_calls` is empty. The agent's tool surface is exactly `search_stories`, `filter_by_dimension`, `describe_theme`,
`compare_stories` — see `docs/architecture.md`.

## Mirror my story

`POST /mirror` — **public, no auth, no dataset required.** Body: `{ story_text, top_k? }`. Embeds the pasted text
with local MiniLM (no OpenAI key needed) and returns its nearest stories in the public seed dataset, plus a computed
narrative fingerprint. Nothing about the submitted text is persisted. Rate-limited per client IP (10 requests / 60s,
in-process) — see `docs/security.md`.

## Evaluation

| Route | Notes |
|---|---|
| `GET /evaluation/run?unit=&top_k=&embedding_model=&dataset_id=` | Runs the gold-query suite now, persists it, and returns the full per-query breakdown. `embedding_model` in the response reflects what was **actually** used after provider-fallback resolution, not necessarily what was requested. |
| `GET /evaluation/runs?dataset_id=&embedding_model=` | Lean history across every run/model, newest first — no per-query detail (see `EvaluationRunSummaryOut`). |
| `GET /evaluation/runs/{id}` | One historical run's full detail, same shape as `/evaluation/run`. |

Metrics: `recall_at_k`, `mrr`, `precision_at_k` (nullable — runs from before this field existed are `null`, not
backfilled), `avg_latency_ms`. See `docs/evaluation.md` for definitions.

## Response schemas

Full request/response models are defined in `backend/app/schemas.py` (Pydantic) and enforced by FastAPI — `/docs`
always reflects the current, exact shape; this page is a map of *what exists and why*, not a mirror of every field.
