# Scaling

This supersedes `architecture.md`'s old "Scaling Path" section from the original 10-story Streamlit prototype — that
plan has now actually been implemented. This document is about what's next past today's scale (hundreds of stories
per dataset, demonstrated up to ~120 in the M6 milestone).

## What's already in place

- **Vector search lives in Postgres**, not in-memory NumPy — `pgvector` + `ivfflat` indexes on both embedding
  columns (see `docs/database_schema.md`). This was the actual M1–M2 migration, not a future plan.
- **Background indexing above a size threshold.** Uploads under `SYNC_INDEX_THRESHOLD` (25 stories,
  `backend/app/services/indexing_service.py`) embed inline for a snappier UX; at or above it, indexing is dispatched
  to Celery and polled via `GET /jobs/{id}`. Clustering follows the same split via `ASYNC_CLUSTER_THRESHOLD`.
- **Idempotent, incremental indexing.** Re-running `/index` or `/reindex` only computes embeddings for
  `(text_unit, model, version)` combinations that don't exist yet — safe to call repeatedly, and re-indexing under a
  new model doesn't recompute or delete the old one.
- **Embedding/model versioning** (`embedding_version`, currently `"v1"`) means a preprocessing or chunking change can
  ship without invalidating already-computed embeddings under the old version.
- **Per-request observability**: `search_logs` (latency, embedding time per `/search` call) and per-job timing
  (`jobs.duration_ms`, `avg_embedding_ms_per_story`) already exist to spot regressions before they're user-visible.

## Vector index tuning

- `ivfflat`'s `lists` parameter should scale roughly with `sqrt(row_count)` — re-tune it (and run `ANALYZE`) after any
  large bulk load; the default used today is tuned for hundreds, not millions, of rows.
- **Move to `hnsw` once recall at the current `ivfflat` settings starts measurably dropping**, or once dataset size
  makes `ivfflat`'s build time impractical. `hnsw` has no training step and better recall/latency at scale, at the
  cost of slower index builds and more memory — right trade once write volume is low relative to read volume, which
  is the expected shape here (index once, search many times).
- Either index type is defined today via raw `op.execute()` in Alembic migrations rather than a SQLAlchemy `Index`
  object — see the migration note in `docs/database_schema.md` before regenerating a migration.

## Ingestion at real scale (beyond hundreds of stories)

- The current sync/async threshold (25 stories) is a single hardcoded constant tuned for "demo-sized" datasets.
  At real scale this becomes a proper cost model — batch size, worker concurrency, and per-story embedding cost
  measured against actual latency budgets rather than one fixed number.
- `MAX_UNITS_PER_STORY` (`indexing_service.py`) already guards against a single pathologically long story producing
  an unbounded number of sentence/passage units — worth revisiting the caps (200 sentences / 60 passages) once
  ingesting longer-form documents than short personal narratives.
- Batch embedding calls (`STORY_BATCH_SIZE = 20`) exist so progress reporting stays granular regardless of dataset
  size; the batch size is itself a knob against provider rate limits once using the OpenAI embeddings path at scale.

## Future experiments (not yet built)

- **UMAP instead of PCA** for the map/projection, once a dataset is large enough that PCA's linear projection starts
  losing neighborhood structure that actually matters for the "hover and explore" experience. Localized to
  `app/clustering.py`'s projection function and the `/clusters/projection` route.
- **HDBSCAN instead of KMeans** — real story collections won't naturally form equally-sized, spherical clusters, and
  KMeans currently requires a manual `k`. HDBSCAN handles varying density and noise points better; worth an
  experiment once there's a large enough real dataset to measure cluster quality against the evaluation dashboard,
  rather than switching defaults without measuring.
- **Narrative arc/timeline detection and theme evolution over time** — both need data this project's current
  datasets don't have (longer-form text for arc detection; a real temporal/cohort field like submission year for
  evolution-over-time). Revisit if a dataset with that structure shows up.

## Deployment (not done in this pass)

Everything above assumes local-first Docker Compose (`docker-compose.yml`: Postgres+pgvector, Redis). Actually
provisioning managed infrastructure (e.g. Neon for Postgres, a managed Redis, Vercel for the frontend, a container
host for the FastAPI/Celery processes) is explicitly out of scope for this pass — secrets are kept in environment
variables and migrations are tool-driven (Alembic) specifically so this replays cleanly against real infrastructure
later without a rewrite.
