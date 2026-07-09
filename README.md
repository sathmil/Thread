# WHO WE ARE Story Explorer

This is a compact embedding-based prototype for structuring a small personal-story dataset. It uses a pretrained sentence-transformer model to embed the stories, then supports:

- Semantic search over the WHO WE ARE stories
- Sentence, passage, and full-story semantic search
- Adjustable thematic clustering with KMeans
- Automatic cluster labels and summaries
- A 2D PCA map of story similarity
- Retrieval evaluation queries
- Enriched story metadata
- Downloadable clustered output
- Optional API-backed embeddings
- CLI commands for search, clustering, and evaluation
- Unit tests for the core retrieval pipeline

The goal is deliberately narrower than training a custom narrative model from scratch: show that messy human data can be made searchable and interpretable quickly with reusable NLP building blocks.

## Current Project State

This project is mid-migration from a Streamlit prototype to a production stack (Next.js + FastAPI + Postgres/pgvector) — see the roadmap for the full plan. The Python retrieval/clustering/evaluation engine now lives under `backend/`:

- `data/stories_metadata.csv`: 10 story records
- `data/story_embeddings.npy`: cached sentence embeddings
- `data/evaluation_gold.csv`: hand-labeled retrieval expectations
- `data/clustered_stories.csv`: an earlier static clustering output
- `backend/app/data.py`: load and enrich stories
- `backend/app/text.py`: split stories into sentence, passage, and document units
- `backend/app/embeddings.py`: local and optional API-backed embedding providers
- `backend/app/search.py`: cosine-similarity ranking
- `backend/app/clustering.py`: KMeans clustering, labels, summaries, and PCA projection
- `backend/app/evaluation.py`: Recall@K and MRR evaluation
- `backend/app/pipeline.py`: reusable index-building pipeline
- `backend/app/cli.py`: command-line interface
- `backend/streamlit_app.py`: interactive Streamlit explorer (prototype UI, being replaced)
- `backend/tests/`: pytest coverage for text processing, data loading, search, clustering, and evaluation
- `docs/architecture.md`: system design and scaling notes
- `docs/demo_walkthrough.md`: demo flow and screenshot checklist
- `docs/evaluation_queries.csv`: repeatable retrieval checks
- `docs/portfolio_summary.md`: portfolio/interview framing
- `docker-compose.yml`: local Postgres+pgvector service (backend API/frontend containers land in later milestones)

## Run It

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

## How The App Works

The sidebar controls the analysis:

- `Theme clusters`: changes how many KMeans groups the story embeddings are divided into.
- `Search results`: changes how many matches appear.
- `Search unit`: switches between sentence-level, passage-level, and full-story search.
- `Embedding backend`: switches between the local pretrained model and optional API-backed embeddings.
- `Semantic search`: accepts natural language queries, embeds the query, and ranks the closest stories or passages with cosine similarity.

The tabs separate the views:

- `Search`: retrieves the most relevant stories or passages for a theme or phrase.
- `Themes`: shows each cluster with generated keywords, a short summary, and story previews.
- `Evaluation`: runs canned queries and shows the top match for each query.
- `Map`: projects the story embeddings into two dimensions with PCA.
- `Dataset`: shows the structured output and lets you download the clustered CSV.
- `Demo`: gives a short walkthrough for presenting the project.

That makes it faster, easier to explain, and more contained than a training-heavy approach while still reinforcing the research theme: turning unstructured human narratives into analyzable structure.

## Resume Framing

Strong SWE bullet:

> Built a semantic retrieval system for unstructured narrative data using sentence embeddings, cosine similarity, KMeans clustering, TF-IDF labeling, and PCA visualization; added sentence-, passage-, and document-level retrieval with Recall@K/MRR evaluation and a reusable CLI.

Shorter version:

> Engineered an embedding-based search and clustering pipeline for qualitative story data, with modular indexing, semantic retrieval, evaluation metrics, and an interactive Streamlit UI.
