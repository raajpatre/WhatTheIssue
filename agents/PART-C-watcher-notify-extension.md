# PART C — Watcher, Notifications (Telegram) + Chrome Extension + Demo Repo

**Read `AGENTS.md` (root) first.** Everything there applies. This file only adds what is specific to Part C.
Owner: ____________

## Your mission
You make the project *alive*. A new matching issue appears on GitHub and a Telegram message lands on a phone. That moment is the centrepiece of our demo, so reliability beats features.

## Your files (and ONLY these)
`backend/app/watcher/service.py`, `backend/app/notify/` (`__init__.py`, `telegram.py`, `telegram_bot.py`), `backend/tests/test_watcher.py`, `extension/`, `scripts/demo_create_issue.py`.
Part A's skeleton already contains stubs with the right signatures. Replace the bodies, keep the signatures.

## C0 — Demo repo (P0, do this first, 15 minutes)
- Create a public repo under the team account, e.g. `myopensource-demo`. Add a README and an MIT licence.
- Open 5 issues by hand: 2 labelled `good first issue` with clear steps, 1 with an assignee, 1 where you comment "I'll take this", 1 with a one-line vague body. You can't fake "stale", and you don't need to.
- Create a **separate** token with issues:write on this repo only, as `DEMO_GITHUB_TOKEN`. Never use the app's `GITHUB_TOKEN` for writes.
- Tell Part B the issue numbers (handy for scoring checks).

## C1 — Watcher (P0, by 7:30 AM; start with stubs, test as soon as A's DB lands)
Implement in `watcher/service.py`:
- `baseline_repo(repo)`: `fetch_new_issues(repo, etag=None)` → `add_seen_issue_ids` for everything returned → `set_etag`. **Sends nothing.** (Without this the first poll would flood users, or swallow a live-created demo issue.)
- `check_all_now() -> {"checked": n, "notified": m}`:
  ```
  for repo in crud.distinct_watched_repos():
      issues, new_etag = github.client.fetch_new_issues(repo, crud.get_etag(repo))
      crud.set_etag(repo, new_etag)
      seen = crud.get_seen_issue_ids(repo)
      fresh = [i for i in issues if i.id not in seen]
      scored = [scoring.score_issue(i) for i in fresh]
      for watch in crud.list_watches(repo=repo):
          for s in scored:
              if labels_match(s.issue.labels, watch.tags) and s.status in ("safe", "unclear"):
                  notify.send(watch.channel, watch.contact, notify.format_alert(s))
      crud.add_seen_issue_ids(repo, [i.id for i in fresh])
  ```
  Wrap each repo in try/except: one failing repo must not stop the rest. Never notify twice for the same issue.
- `start_scheduler()`: if `ENABLE_SCHEDULER=1`, start an APScheduler background job running `check_all_now` every `POLL_INTERVAL_MINUTES`. Guard against double-start (uvicorn reload). If `ENABLE_TELEGRAM_BOT=1`, also start the bot thread.
- Tests: mock the GitHub client, DB and notify. Cover: first run baseline, new matching issue notifies once, claimed issue skipped, non-matching label skipped, one repo failing.

## C2 — Telegram (P0)
- `notify/telegram.py`: `sendMessage` via HTTPS to the Telegram Bot API with `TELEGRAM_BOT_TOKEN` (# VERIFY the endpoint in Telegram's docs). **Escape any HTML** in issue titles (untrusted text), or send plain text.
- `notify/__init__.py`: `send(channel, contact, text) -> bool` (never raises; log the failure without secrets) and `format_alert(scored)`: repo, title, status + score, up to 2 reasons, link. Short.
- `notify/telegram_bot.py`: long polling (`getUpdates`), no public webhook needed. Commands:
  - `/start` → replies with the user's **chat ID** and how to use the commands (the web form needs this ID).
  - `/track owner/repo [tag1,tag2]` → `crud.create_watch` + `baseline_repo`.
  - `/list` → their watches. `/untrack <id>` → `crud.delete_watch`.
- **Only ONE process may long-poll a bot token** (otherwise Telegram returns 409). That's why it's gated by `ENABLE_TELEGRAM_BOT`. Tell the team: only the deployed server (and you, when testing) turns it on.
- Email channel: **P2, skip unless everything else is done.**

## C3 — Demo script (P0, 20 minutes)
`scripts/demo_create_issue.py`: creates ONE new issue with a `good first issue` label in `DEMO_REPO` using `DEMO_GITHUB_TOKEN`. **Refuse to run if the target repo is not exactly `DEMO_REPO`.** This is the only write operation in our whole project (event rule: fork, don't spam). Print the issue URL.
Demo flow to rehearse: track the demo repo → run the script → press "Check now" in the UI (or wait for the poll) → the Telegram alert arrives.

## C4 — Chrome extension (P2: start ONLY after C1–C3 work, no earlier than 7:30 AM, hard stop 8:30 AM)
- Manifest V3 in `extension/`. `host_permissions`: `https://github.com/*` and the API origin. Content script matches `https://github.com/*/*`.
- Only act on real repo pages: path has owner and repo, and the first segment is not a GitHub reserved path (`settings`, `orgs`, `topics`, `marketplace`, `notifications`, `explore`, `pulls`, `issues`, `login`, etc.).
- **Fetch through the background service worker**, not the content script (page CORS would block the content script). The content script sends a message; the worker calls `GET {API_BASE}/api/repos/{owner}/{name}/issues?status=safe` and caches the result in `chrome.storage.session` for 10 minutes.
- UI: a small floating badge, bottom right: "N beginner-safe issues" plus **Track** and **Open in myOpenSource** buttons. Track asks for the Telegram chat ID once (stored in `chrome.storage.sync`) then `POST /api/watch`.
- Build the DOM with `textContent` / `createElement`. **Never `innerHTML` with API data.** No `eval`, no remote scripts, minimal permissions.
- `extension/config.js` holds `API_BASE`. Load unpacked for the demo; no store publishing.
- Add a short `extension/README.md` (load-unpacked steps) and credit anything you use.

## Definition of done
- Create an issue in the demo repo → Telegram message arrives within one poll (or one "Check now"). No duplicates.
- `/start`, `/track`, `/list`, `/untrack` work. `pytest` green. No tokens in git.

## Don'ts
- Don't write to any repo except `DEMO_REPO`. Don't edit API routes, DB code, scoring, AI or the frontend. Don't start the Telegram bot or scheduler by default.
