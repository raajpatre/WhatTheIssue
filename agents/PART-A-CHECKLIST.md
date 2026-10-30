# Part A checklist

Work only the items in `PART-A-core-backend.md`. Do not implement scoring, AI, watcher, frontend, or the extension.

Pulled `origin/main` (Part B scoring/AI merged in PR #3). Kept Part A `schemas.py` and `labels.py`. Kept Part B scoring, AI, and their tests.

## Step 0 — Skeleton (P0)

- [x] Layout, MIT `LICENSE`, `.gitignore`, `.env.example`, `CREDITS.md`, README stub, fixtures
- [x] `schemas.py` copied verbatim from the contract
- [x] `normalize_label` / `labels_match` in `github/labels.py`
- [x] `config.py` env vars; scheduler and Telegram bot default OFF
- [x] B/C stubs with exact signatures (`scoring`, `ai`, `watcher`, `notify`)
- [x] FastAPI + CORS `allow_origins=["*"]`; startup calls `watcher.start_scheduler()`
- [x] All `/api` paths exist with contract shapes
- [x] `backend/tests/test_health.py`
- [x] Skeleton on a PR (`a/skeleton`)

## P0 — GitHub client

- [x] `httpx` GET-only client; Bearer / Accept / User-Agent / API version (`# VERIFY`)
- [x] `parse_repo` (URL, `.git`, slash, extra path, `owner/name`)
- [x] `fetch_issues`: 2 pages, drop PRs, client-side `labels_match`, cap `limit`
- [x] Latest 10 comments + open linked PR from timeline; per-issue fallback
- [x] `fetch_readme` raw text or `""`
- [x] `fetch_new_issues` ETag / HTTP 304
- [x] `RateLimitError` / `RepoNotFoundError` / `UpstreamError`

## P0 — DB

- [x] SQLAlchemy sync + SQLite, WAL, `check_same_thread=False`
- [x] Tables: repos, issues, seen_issues, ai_insights, watches
- [x] Every contract CRUD function; each call opens and closes its own session

## P0 — API orchestration

- [x] `POST /api/repos` → parse → fetch → rank → upsert → `{repo, issues, note}`
- [x] `GET .../issues` 5-min cache, status filter, attach cached AI
- [x] `GET .../explain` cache → load/fetch → `ai.explain_issue` → save
- [x] `GET .../suggestions` README → AI, 1-hour cache
- [x] `POST /api/watch` + `baseline_repo`; `POST /api/watch/check-now`
- [x] Blocking GitHub/AI/watcher calls in `run_in_threadpool`
- [x] `{"error": {"code", "message"}}` for INVALID_REPO / REPO_NOT_FOUND / RATE_LIMITED / UPSTREAM_ERROR

## P1

- [x] Log GitHub remaining quota (no secrets)
- [x] Human `RATE_LIMITED` message
- [x] Deploy config (`render.yaml`); env vars stay in the host dashboard, never git
- [x] Document no-scope GitHub token; scheduler/bot flags ON only on the deployed server

## P2

- [x] Per-IP request throttle on `/api` (health exempt)

## Definition of done

- [x] `pytest` green
- [x] Local `uvicorn` boot + every contract endpoint returns the exact shape
- [x] Bad repo URL → `INVALID_REPO`
- [x] No secrets in git
