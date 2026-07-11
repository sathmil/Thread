# Security

This is a portfolio/demo project, local-first and not yet deployed — this document is written the way a real
pre-launch security review would be: what's actually in place, and what's explicitly not, rather than implying more
coverage than exists.

## Authentication

- Clerk issues a JWT; the backend verifies it against Clerk's JWKS endpoint (`CLERK_JWKS_URL`,
  `backend/app/auth.py`) using `PyJWKClient` + RS256 verification — the signature is actually checked, not just the
  payload trusted.
- `get_current_user` resolves to `None` (not an error) when no token is sent, so public routes and public datasets
  work fully signed-out. Only `require_user` (dataset creation, upload, index/reindex) actually rejects
  unauthenticated requests with a `401`.
- Until `CLERK_JWKS_URL` is configured, sign-in is inert everywhere (frontend shows "Sign in (not configured)") but
  every public route still works — this was the explicit fallback path verified at the M5 milestone in this
  environment, since no live Clerk instance was configured here.
- A `User` row is created lazily on first authenticated request, keyed by `clerk_user_id`. There's no separate
  password or credential store — Clerk owns that entirely.

## Authorization / dataset scoping

- Every dataset has a `visibility` (`private|public`) and a nullable `owner_user_id`. `dataset_service.py` centralizes
  the rule: public datasets are readable by anyone; private datasets require the caller to be signed in **and** be
  the owner, otherwise `401` (no token) or `403` (wrong user) — never a silent empty result.
- Mutating routes (`upload`, `index`, `reindex`) additionally require the caller to be the dataset's owner even if
  they could otherwise read it — checked explicitly in `datasets.py`'s `_require_owner`, not just inherited from the
  read-scoping check.
- Story-level routes (`/stories/{id}`, `.../fingerprint`, `.../journey`) resolve the story's dataset and apply the
  same scoping rather than trusting the story id alone to imply access.
- Evaluation run history (`/evaluation/runs/{id}`) is scoped the same way — confirmed by a dedicated test
  (`test_get_run_detail_requires_dataset_scoping`).

## Rate limiting

**Only one route has a rate limit today: `POST /mirror`** (10 requests / 60 seconds per client IP, in-process
`dict`, `backend/app/routers/mirror.py`). It's the only fully public, unauthenticated, write-adjacent route — no
account, no dataset ownership check, nothing to gate it otherwise — so it was flagged for this specifically in the
roadmap.

**Known gap:** no other route is rate-limited. `/query` (the conversational agent, which calls OpenAI when
configured) and `/search`/`/index`/`/reindex` (which can trigger embedding-provider calls) have no per-user quota.
This matters most once real OpenAI credentials are in play — an unrate-limited authenticated user could still run up
API cost through repeated searches, re-indexes, or agent questions. A basic per-user daily quota check before any
OpenAI-backed call (embeddings, chat, tool-calling) was flagged in the roadmap as a follow-up once this moves past a
demo, not yet implemented.

**Known gap:** the `/mirror` rate limiter is an in-process Python `dict` — correct for a single worker process, but
would under-count (or double-count, depending on load balancing) across multiple backend processes/replicas. A real
deployment would need a shared store (Redis, which is already a dependency for Celery) instead.

## Secrets

- All secrets (`DATABASE_URL`, `OPENAI_API_KEY`, `CLERK_JWKS_URL`) are read from environment variables
  (`.env`, gitignored; `.env.example` documents every key with no real values). None are committed, and none are
  logged.
- Every OpenAI-backed feature (embeddings, fingerprint scoring, theme reports, insight phrasing, the conversational
  agent) has a deterministic fallback when the key is absent — this is a reliability property as much as a security
  one: the app never silently requires a secret to be minimally functional.

## Transport / CORS

- **Known gap, dev-only as written:** CORS (`backend/app/main.py`) allows exactly `http://localhost:3000` — correct
  for local development, but would need to be the real deployed frontend origin (and nothing else) before any real
  deployment. There's no wildcard origin today, which is the right default to *not* accidentally ship permissively.
- No HTTPS enforcement exists because there's no deployment yet — this is infrastructure-layer, not
  application-layer, and belongs with whatever hosts the eventual deployment (e.g. a platform that terminates TLS in
  front of the app).

## Input handling

- CSV upload (`/datasets/{id}/upload`) requires a `story_text` column and rejects anything else with a `422`, parsed
  via `pandas.read_csv` from an in-memory buffer — no file is ever written to disk from user input.
- All database access goes through SQLAlchemy's parameterized query builder (`select(...)`, `.where(...)`) — no raw
  string-interpolated SQL anywhere in the routers or services, so standard SQL injection via user-supplied query
  text (search queries, mirror text, agent questions) isn't a live vector.
- The conversational agent's tool surface is deliberately narrow (exactly `search_stories`, `filter_by_dimension`,
  `describe_theme`, `compare_stories` — see `docs/architecture.md`) specifically so a crafted natural-language
  question can't make the agent do anything the rest of the app couldn't already do through its normal UI.

## Observability

`search_logs` and per-job timing exist today for performance observability, not security auditing — there's no
structured audit log of who accessed/modified what dataset when. Worth adding before handling data more sensitive
than the current demo dataset (already-public personal narrative excerpts).
