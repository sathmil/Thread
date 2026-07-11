# Thread — Find yourself in someone else's experience

An AI-powered interface for exploring human experience at scale: an explorable story map, semantic search, a
conversational agent, "mirror my story" (paste your own narrative and see who else has felt the same way), theme
summaries, and a statistical insight engine — all built on Next.js, FastAPI, Postgres/pgvector, Clerk, and Celery,
with every OpenAI-backed feature degrading gracefully to deterministic logic when no API key is configured.

See `docs/architecture.md` for the full system design (including the Story/Theme/Journey/Insight product model this
is organized around), `docs/api.md` for the route reference, `docs/database_schema.md` for the data model,
`docs/scaling.md` and `docs/evaluation.md` for the retrieval/evaluation system in depth, `docs/security.md` for the
auth/scoping model and known gaps, and `docs/demo_walkthrough.md` for a guided tour.

## Current Project State

The production stack (Next.js + FastAPI + Postgres/pgvector + Clerk + Celery) below is the primary way to run this
project; the original Streamlit prototype (`backend/streamlit_app.py`) still exists and still runs, kept as-is
rather than deleted, but is no longer how this project is meant to be used or demoed. Its retrieval/clustering/
evaluation logic (`backend/app/search.py`, `clustering.py`, `evaluation.py`, `text.py`, `data.py`) was carried forward
into the production stack rather than rewritten — see `docs/architecture.md`'s "Reused from the original prototype"
section.

- `data/`: the original 10-story seed dataset + hand-labeled evaluation queries, loaded by `backend/scripts/seed.py`.
- `backend/app/`: FastAPI app — `routers/` (HTTP layer), `services/` (the actual logic), `models.py` (SQLAlchemy),
  `tasks.py`/`celery_app.py` (background indexing).
- `backend/alembic/`: schema migrations.
- `backend/tests/` (pure retrieval/clustering/evaluation logic) and `backend/tests/api/` (FastAPI integration tests).
- `frontend/`: Next.js app — see `docs/architecture.md` for the full page list.
- `.github/workflows/ci.yml`: backend pytest against a real Postgres+pgvector service container, frontend lint/
  typecheck/test/build.
- `docker-compose.yml`: local Postgres+pgvector and Redis services.

## Running the Full Stack (Next.js + FastAPI + Postgres/pgvector + Celery)

The project is now a FastAPI backend + Next.js frontend behind Postgres/pgvector, with Celery+Redis for background
indexing jobs (uploaded datasets embed asynchronously above ~25 stories). The Streamlit app below still exists as
the original prototype but is no longer the primary way to run this.

```bash
# 1. Infra
docker compose up -d db redis

# 2. Backend API (new terminal)
cd backend && source ../myenv/bin/activate
alembic upgrade head          # first time / after schema changes
python -m scripts.seed        # first time, seeds the public 10-story dataset
uvicorn app.main:app --port 8000

# 3. Celery worker, for background dataset indexing (new terminal)
cd backend && source ../myenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=solo
```

> **macOS note:** use `--pool=solo` (not the default prefork pool) for the Celery worker. Prefork forks a child
> process per worker, and PyTorch/Metal (used internally by `sentence-transformers`) isn't fork-safe on macOS —
> the child crashes with `+[MPSGraphObject initialize] ... Crashing instead` the first time it embeds anything.
> `--pool=solo` avoids the fork entirely. This only matters for local dev; a containerized worker in a real
> deployment wouldn't hit this.

```bash
# 4. Frontend (new terminal)
cd frontend && npm run dev
```

Then open `http://localhost:3000`. To exercise the upload → index → search flow at scale without a real Clerk
account yet, see `backend/scripts/demo_large_upload.py` (drives the API directly via `TestClient`, bypassing auth
with a dependency override — the same pattern the test suite uses).

## Running the Original Streamlit Prototype

This is the pre-migration prototype — kept runnable for reference, not the primary way to use this project (see
above). It's a single-dataset, no-auth, in-memory version of the same retrieval/clustering/evaluation logic.

```bash
source myenv/bin/activate
cd backend
streamlit run streamlit_app.py --server.fileWatcherType none
```

If the cached embeddings are missing or out of date, the app regenerates them with `all-MiniLM-L6-v2`.

The `--server.fileWatcherType none` flag avoids noisy Streamlit watcher logs from optional transformer vision modules.

## Optional API Embeddings

The app defaults to local MiniLM embeddings so it works offline. To test the API-backed path:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
cd backend && streamlit run streamlit_app.py --server.fileWatcherType none
```

Then choose `OpenAI API` in the sidebar.

## CLI

```bash
cd backend
python -m app.cli search "finding my voice" --unit Passages --top-k 5
python -m app.cli cluster --clusters 4
python -m app.cli evaluate --unit Passages --top-k 3
```

## Tests

```bash
cd backend
pytest
```

The tests use deterministic small fixtures where possible, so they do not require downloading a model.

## Technique

This version avoids custom training. It uses:

- `sentence-transformers/all-MiniLM-L6-v2` for sentence embeddings
- Cosine similarity for semantic query search over full stories or passages
- KMeans for quick theme discovery
- TF-IDF terms for readable cluster names
- Rule-based focus tags and cluster summaries for interpretability
- PCA for a lightweight visual map
- Recall@K and MRR for retrieval evaluation

The prototype's sidebar/tabs (Search, Themes, Evaluation, Map, Dataset) map directly onto the production frontend's
pages — see `docs/demo_walkthrough.md` for the current equivalents plus the features that only exist in the
production stack (Ask, Mirror, Insights, per-story Journeys).

## Portfolio / Interview Framing

See `docs/portfolio_summary.md` for the current framing — it supersedes any resume bullet written for the original
Streamlit-only version of this project.
