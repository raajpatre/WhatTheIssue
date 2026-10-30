# PART A — Core Backend (GitHub ingestion, DB, REST API, deploy) · the SPINE

**Read `AGENTS.md` (root) first.** Everything there applies. This file only adds what is specific to Part A.
Owner: ____________ (integration lead: you resolve merge conflicts and keep `main` bootable)

## Your mission
You build the spine every other part plugs into. If you are late, three other people are blocked, so **Step 0 is the most important task of the night.**

## Your files (and ONLY these)
`backend/app/main.py`, `config.py`, `schemas.py`, `api/`, `db/`, `github/`, `backend/requirements.txt` (shared, append-only), `LICENSE`, `.gitignore`, `.env.example`, deploy config.
In Step 0 you also create **stub files for the other parts**. After the skeleton is merged, those files belong to their owners. Never touch them again.

## Step 0 — SKELETON (P0, finish by 12:30 AM, push straight to `main`)
1. Create the layout from `AGENTS.md`. Add `LICENSE` (MIT), `.gitignore`, `.env.example` (from the contract), `CREDITS.md`, README stub, `agents/` (copy the 4 part files), `fixtures/sample_issues.json`.
2. `schemas.py`: copy the models from `AGENTS.md` **verbatim**.
3. `github/labels.py`: implement `normalize_label` and `labels_match` fully (tiny, everyone depends on them).
4. `config.py`: read env vars with safe defaults (scheduler and bot default OFF).
5. **Stubs with the exact contract signatures** (return dummy values):
   - `scoring/engine.py`: `score_issue` returns score 50, status `"unclear"`; `rank` returns them sorted.
   - `ai/service.py`: `explain_issue` returns a placeholder `AIInsight`; `suggest_from_readme` returns 1 placeholder suggestion.
   - `watcher/service.py`: `start_scheduler`, `baseline_repo`, `check_all_now` (returns zeros).
   - `notify/__init__.py`: `send` (returns True), `format_alert`.
6. `main.py`: FastAPI app, CORS `allow_origins=["*"]` (public read API, no cookies, no credentials), include routers, on startup call `watcher.start_scheduler()`.
7. `api/`: ALL endpoints from the contract table. In the skeleton they may return fixture data, but **paths, bodies and response shapes must already be exact.**
8. `backend/tests/test_health.py` (one test hitting `/api/health`).
9. Push to `main`. Message the group: "skeleton is live, pull now".

## P0 — Real GitHub client (`github/client.py`) — by 2:30 AM
- Use `httpx`. Headers: `Authorization: Bearer <GITHUB_TOKEN>`, `Accept: application/vnd.github+json`, `User-Agent: myopensource`. Check the API-version header against current GitHub docs (# VERIFY).
- `parse_repo`: accept `https://github.com/owner/name`, with `.git`, trailing slash, extra path (`/issues`), or plain `owner/name`. Raise `ValueError` otherwise.
- `fetch_issues`: `GET /repos/{owner}/{name}/issues?state=open&per_page=100` (up to 2 pages). **This endpoint also returns pull requests: drop any item that has a `pull_request` key.** Filter by `labels_match` client-side (do not rely on the `labels=` query param; it ANDs labels and misses variants). Cap at `limit` issues.
- For each kept issue: fetch the latest 10 comments (cap concurrency around 8 with a thread pool) and detect an open linked PR from the issue timeline (`cross-referenced` events from a PR that is still open; # VERIFY exact fields). If a call fails, fall back to `linked_pr_open=False` and `comments=[]`. Never crash the whole list.
- `fetch_readme`: `GET /repos/{o}/{n}/readme` with `Accept: application/vnd.github.raw+json`. Return plain text, `""` if none.
- `fetch_new_issues`: page 1, `sort=created&direction=desc&per_page=30`, send `If-None-Match` with the stored ETag; on 304 return `([], etag)`.
- Rate limits: if remaining is 0 or the status is 403/429 → raise `RateLimitError`. 404 → `RepoNotFoundError`. Anything else → `UpstreamError`. The API layer maps these to the contract error codes.
- **Read-only.** Only GET requests, ever.

## P0 — DB (`db/`) — by 2:30 AM
- SQLAlchemy (sync) + SQLite. Enable WAL mode and `check_same_thread=False` (the scheduler runs on another thread).
- Tables: `repos(full_name, etag, last_fetched_at)`, `issues(id, repo, number, json, updated_at)`, `seen_issues(repo, issue_id)` unique pair, `ai_insights(repo, number, json, created_at)`, `watches(id, repo, tags_json, channel, contact, created_at)`.
- `crud.py` implements every function listed in the contract. Each opens and closes its own session.

## P0 — Orchestration (`api/`) — by 3:30 AM
- `POST /api/repos`: `parse_repo` → `fetch_issues(tags)` → `scoring.rank` → `upsert_issues` → respond. If empty, set `note`.
- `GET .../issues`: same, but use the 5-minute in-memory TTL cache keyed by (repo, tags). Apply `status` filter after scoring. If a cached AI insight exists, attach it as `ai`.
- `GET .../explain`: `crud.get_ai_insight` → else load the issue (`crud.get_issue`, or fetch live) → `ai.explain_issue` → `save_ai_insight` → return.
- `GET .../suggestions`: `fetch_readme` → `ai.suggest_from_readme`; cache in memory 1 hour.
- `POST /api/watch`: validate repo, `create_watch`, then `watcher.baseline_repo(repo)`.
- `POST /api/watch/check-now`: `watcher.check_all_now()`.
- **Blocking functions (GitHub, AI) must run in a threadpool** (`run_in_threadpool` / `asyncio.to_thread`) so the server does not freeze.
- Global exception handler → the `{"error": {...}}` shape from the contract.

## P1
- Rate-limit friendliness: log remaining quota (no secrets), return `RATE_LIMITED` with a human message.
- Deploy backend (pick a free host and check its current free-tier limits; # VERIFY). Set env vars in the host dashboard, never in git. Set `ENABLE_SCHEDULER=1` and `ENABLE_TELEGRAM_BOT=1` **only on the deployed server**.
- Give the app a GitHub token with minimal or no scopes (public data only).

## P2
- Simple per-IP request throttle so a stranger cannot burn our GitHub quota.

## Definition of done
- Fresh clone + `.env` → `uvicorn app.main:app` boots; every endpoint in the contract answers with the exact shape.
- Pasting a real repo link returns scored issues; bad links return `INVALID_REPO`.
- `pytest` passes. No secrets in git history.

## Don'ts
- Don't change contract shapes without the `contract:` PR process. Don't add features the contract does not list. Don't write scoring, AI, watcher, frontend or extension logic.
