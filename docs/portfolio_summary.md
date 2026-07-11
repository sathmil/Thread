# Portfolio Summary

## Title

Thread — Find yourself in someone else's experience

## Short description

An AI-powered interface for exploring human experience at scale. Paste your own story and see who else has felt the
same way, ask questions in plain language and get answers grounded in real retrieval, or just explore a map of
hundreds of personal narratives — hover, click, and follow the threads between them. Underneath, it's a full
production stack: Next.js, FastAPI, Postgres/pgvector, Celery, and an optional LLM layer that degrades gracefully to
deterministic logic when no API key is configured.

## Why it matters

Human stories are hard to analyze because the signal is thematic, not keyword-based, and because "here are 200
similar documents" isn't actually useful to a person — "here's why this one resonates with you, specifically" is.
This project is built around four user-facing objects — **Story**, **Theme**, **Journey**, **Insight** — chosen
because none of them are specific to personal narratives: the same architecture works for interview transcripts,
oral histories, therapy reflections, or research responses. Narrative fingerprints, embeddings, and cluster runs are
implementation details that power those four objects; they're deliberately never the headline feature.

## Technical highlights

- **Full-stack production architecture**: Next.js 16 + TypeScript + TanStack Query frontend, FastAPI backend,
  Postgres + pgvector, Clerk auth, Celery + Redis for background jobs — not a notebook or a single script.
- **Real vector search**, not in-memory NumPy: pgvector cosine-distance queries with `ivfflat` indexes, dual
  fixed-width columns to support two embedding providers (MiniLM 384-dim, OpenAI 1536-dim) without a schema rewrite.
- **Idempotent, versioned indexing**: re-indexing a dataset under a new embedding model never deletes the old one;
  old and new stay queryable side by side for direct comparison.
- **A tool-calling conversational agent** (`/ask`) with a deliberately narrow tool surface — it can't retrieve or
  assert anything the rest of the app couldn't already show directly, by design, not by accident.
- **A statistical insight engine**, not an LLM making things up: every finding (correlations across narrative
  dimensions, standout stories) is computed from real embeddings/fingerprints and thresholded by effect size and
  sample size before being surfaced; an LLM may only rephrase a confirmed finding, never assert one.
- **"Mirror my story"**: paste an ad hoc narrative, no account needed, and get real matches from local embeddings —
  works with zero external API keys.
- **Every OpenAI-backed feature has a deterministic fallback** (keyword-heuristic fingerprints, rule-based theme
  summaries, a plain "not configured" message from the conversational agent) — the app is never broken by a missing
  API key, it's just less fluent.
- **An evaluation dashboard that's a first-class feature**, not an afterthought: Recall@K/MRR/Precision@K, a score
  distribution, and full historical/model-vs-model comparison, all backed by every run being persisted automatically.
- **CI enforced from day one of this milestone sequence**: GitHub Actions runs the full backend suite against a real
  Postgres+pgvector service container and the full frontend lint/typecheck/test/build — not just on a laptop.

## Interview framing

The engineering answers "can this scale and hold up under real infrastructure constraints" — versioned embeddings,
idempotent background jobs, a real vector database, CI against a real service container. The product answers "would
anyone actually use this more than once" — a homepage you can spend a few minutes exploring rather than a search box,
a Journey that explains *why* two stories resonate instead of just asserting similarity, and a mirror-my-story flow
that makes the tool about *you*, not just the dataset. Both halves were built deliberately, in that order, because a
technically excellent retrieval system that nobody wants to open twice isn't actually the harder problem to solve.
