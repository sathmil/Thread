# Evaluation

Retrieval evaluation is treated as a first-class part of this project, not an afterthought bolted on at the end — a
basic version shipped in the M2 milestone (the same milestone that introduced the API), and it was deepened (not
started) at M8.

## Gold queries

`backend/scripts/seed.py` loads hand-labeled query → expected-story mappings (originally `data/evaluation_gold.csv`
from the pre-migration prototype) into `evaluation_queries` / `evaluation_query_expected_stories` — normalizing what
was a pipe-separated CSV column into a proper join table. A gold set stays scoped to its designated dataset; it's
not assumed to represent an organically growing corpus.

## Metrics

Computed per query, then averaged into a run (`backend/app/services/evaluation_service.py`):

- **Recall@K** — did *any* expected story appear in the top K results?
- **MRR (Mean Reciprocal Rank)** — how early did the *first* expected story appear, across the full ranking (not
  truncated at K)?
- **Precision@K** — what *fraction* of the top K results were actually expected? Distinct from Recall@K: a query
  with 3 expected stories that surfaces only 1 of them in the top 3 has perfect recall (a hit occurred) but
  precision 1/3.
- **Latency** — per-query and averaged per run (`avg_latency_ms`), captured around the same search call used for
  scoring, not a separate synthetic benchmark.

`precision_at_k` was added to the `evaluation_runs` schema before it was actually computed (an early migration
included the column; M8 is what started populating it) — runs from before that are `null`, not backfilled, and both
the API and frontend treat the field as nullable throughout rather than assuming every historical row has a value.

## Running an evaluation

`GET /evaluation/run?unit=&top_k=&embedding_model=&dataset_id=` runs the full gold-query suite against the current
index **and persists it** as a new row — every call is a permanent history entry, not a stateless computation. The
`embedding_model` recorded is what was **actually** used after provider-fallback resolution (see
`docs/database_schema.md`), not necessarily what was requested — a run requested under `"OpenAI API"` with no
`OPENAI_API_KEY` configured is honestly recorded as `"Local MiniLM"` rather than mislabeling itself.

## Historical & model-comparison view

Because every run is persisted, `GET /evaluation/runs` (a lean summary, no per-query detail) and
`GET /evaluation/runs/{id}` (full detail) are enough to build a proper comparison view with no separate "save this
run" step. The `/evaluation` frontend page's History table doubles as the model-comparison view: MiniLM vs. OpenAI,
or a run before and after a re-index, sit side by side and clicking any row loads its full per-query breakdown in
place of the live-run panel.

## CI smoke test

`backend/tests/api/test_evaluation.py::test_evaluation_run_matches_known_metrics` asserts Recall@K/MRR against the
seeded 10-story dataset's known values (`recall_at_k ≈ 0.857`, `mrr ≈ 0.893` at `unit=Passages, top_k=3`). Because
CI (`.github/workflows/ci.yml`) runs the exact same seed script against a fresh Postgres container before running
pytest, this test doubles as the roadmap's "evaluation smoke test, asserts metrics don't regress" — a real retrieval
regression fails CI directly, not just a unit test in isolation. The workflow explicitly caches and pre-downloads
the MiniLM model weights so this reflects real embeddings, not a network-outage fallback.

## Known limitations

- Gold queries are hand-labeled and small (10-story seed dataset) — a good repeatability check, not a statistically
  powered benchmark. Don't read small differences in Recall@K between runs as significant.
- There's no held-out query set separate from the one used for iteration — the gold set doubles as both the tuning
  signal and the regression check, which is fine at this scale but wouldn't be if the retrieval logic were being
  actively tuned against these exact numbers.
