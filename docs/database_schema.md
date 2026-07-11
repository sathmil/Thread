# Database Schema

Postgres + the `pgvector` extension. Managed by Alembic (`backend/alembic/versions/`); the ORM models are the source
of truth (`backend/app/models.py`).

## Core tables

| Table | Purpose |
|---|---|
| `users` | One row per Clerk user, keyed by `clerk_user_id`; created lazily on first authenticated request. |
| `datasets` | `owner_user_id` nullable (the public seed dataset is ownerless); `visibility` (`private\|public`), `status` (`draft\|indexing\|ready\|failed`), `default_cluster_k`. |
| `stories` | Dataset-scoped; keeps the uploaded CSV's own id as `external_id` (unique per dataset, not globally). |
| `text_units` | Sentence/passage/story-level chunks of a story; `(story_id, unit_type, unit_index)` unique. Chunking is model-independent, which is what makes re-indexing under a new embedding model cheap (see below). |
| `embeddings` | One row per `(text_unit, embedding_model, embedding_version)`. |
| `clusters` / `cluster_assignments` | Grouped by `cluster_run_id`; scoped per-dataset (not global, unlike the original prototype). `clusters.summary_source` is `rule_based\|llm`. |
| `story_fingerprints` | Narrative-fingerprint scores per `(story_id, model, version)`; `summary_source` is `rule_based\|llm`. |
| `insight_findings` | Persisted insight-engine output; `finding_type` enum, nullable `subject_story_id`, nullable `dimension_a`/`dimension_b`, `effect_size`, `sample_size`, `embedding_model`. |
| `evaluation_queries` / `evaluation_query_expected_stories` | Gold queries and their expected stories (normalizes what was a pipe-separated CSV column in the original prototype). |
| `evaluation_runs` / `evaluation_results` | One row per run (with `recall_at_k`, `mrr`, `precision_at_k`, `avg_latency_ms`) and one row per query within that run. |
| `search_logs` | Timing/observability for every `/search` call (latency, embedding time). |
| `jobs` | Celery job status/progress for `/index` and `/reindex`. |

## Embeddings: two vector columns, not one

MiniLM is 384-dimensional; OpenAI's `text-embedding-3-small` is 1536-dimensional. Rather than one variable-width
column, `embeddings` has two nullable, fixed-width columns:

```
vector_384  vector(384)
vector_1536 vector(1536)
dim         integer   -- which one is populated, so callers don't have to guess
```

Each has its own `ivfflat` index (`vector_cosine_ops`). The dimension→column mapping is centralized in
`backend/app/services/embedding_columns.py` rather than scattered across call sites — a real bug from the M7
milestone (embeddings always written to `vector_384` regardless of actual length) motivated pulling this into one
place. A third provider/dimension in the future adds a third nullable column, not a schema rewrite.

## Provider label vs. model id — a distinction worth remembering

`"Local MiniLM"` / `"OpenAI API"` are UI-facing **provider labels** — they select which `embed_texts()` code path
runs. The **model id** actually stored in and queried from `embeddings.embedding_model` /
`clusters.embedding_model` is a real identifier (`all-MiniLM-L6-v2`, `text-embedding-3-small`). Conflating the two
was a real M7 bug: the seed script stored the model id while a newly-added correctness filter compared against the
provider label, silently returning zero search results. `embedding_columns.py`'s `model_id_for_provider()` /
`resolve_provider()` are the fix — every service that takes a provider label converts it before touching the
database.

## Idempotent indexing

`index_dataset()` reuses existing `text_units` (chunking doesn't depend on the embedding model) and only inserts
`embeddings` rows for `(text_unit, model, version)` combinations that don't already exist. That's what makes
`/reindex` safe to call repeatedly, under the same or a different model, without ever deleting a prior model's
embeddings or clusters — old and new coexist for the evaluation dashboard's model comparison.

## Vector indexing

`ivfflat` with `vector_cosine_ops`, tuned via `lists ≈ sqrt(row_count)` and an `ANALYZE` after bulk loads. See
`docs/scaling.md` for when to move to `hnsw` instead.

## Migration notes

- Alembic autogenerate reliably (and incorrectly) flags the `embeddings` table's `ivfflat` indexes as "removed" on
  every unrelated migration, because they're raw SQL (`op.execute(...)`), not SQLAlchemy `Index` objects. Every
  generated migration in this repo has those lines manually stripped from `upgrade()`/`downgrade()` — check for this
  before trusting a fresh autogenerate diff.
- `precision_at_k` on `evaluation_runs` existed in the schema from an early migration but was only actually computed
  starting at the M8 milestone — older rows have it `NULL` rather than backfilled, and the API/frontend treat it as
  nullable throughout rather than assuming every row has a value.
