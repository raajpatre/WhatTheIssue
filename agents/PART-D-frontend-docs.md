# PART D — Frontend (React) + README + Demo Script

**Read `AGENTS.md` (root) first.** Everything there applies. This file only adds what is specific to Part D.
Owner: ____________

## Your mission
You build the face of the product and the story judges see. A beginner should understand the screen in 5 seconds: *paste a repo, see which issues are safe to start, understand them, track the repo.*

## Your files (and ONLY these)
`frontend/`, `README.md`, `docs/demo-script.md`, and you curate `CREDITS.md` (everyone appends; you tidy it at the end).

## Stack
Vite + React. Tailwind is fine if it speeds you up. Env: `VITE_API_BASE` (default `http://localhost:8000`) and `VITE_USE_MOCK=1`.
**The browser never talks to GitHub directly and never holds a token.** Everything goes through our `/api`.

## D0 — Mock-first (P0, start immediately, do not wait for the backend)
- Copy `fixtures/sample_issues.json` into `frontend/src/mock/` (copy it, never edit the original).
- Put every network call in ONE module, `src/api.js`, exposing: `analyzeRepo(url, tags)`, `getIssues(repo, tags, status)`, `getSuggestions(repo)`, `explainIssue(repo, number)`, `createWatch(w)`, `listWatches(contact)`, `deleteWatch(id)`, `checkNow()`. With `VITE_USE_MOCK=1` they return mock data after a short fake delay; otherwise they call the real endpoints from the contract table. Shapes must match `AGENTS.md` exactly (`ScoredIssue`, `AIInsight`, ...).
- Switching to the real backend must be a one-line env change.

## D1 — Screens (P0, by 3:30 AM)
1. **Home**: repo URL input, tag chips (default `good first issue`; offer `help wanted`, `beginner`, plus a custom tag), **Analyze** button.
2. **Results**: repo header and two tabs, **Issues** and **From the README**.
   - Issue card: title (opens GitHub in a new tab with `rel="noopener noreferrer"`), status badge (`safe` green, `unclear` grey, `stale` amber, `claimed` red), score bar, `reasons` as a short list, labels, and an **Explain this issue** button that lazily calls `explainIssue` and shows summary, files to touch, first steps and the beginner rating.
   - Filter: by default show `safe` and `unclear`; a toggle shows `claimed` and `stale` too.
   - If `note` is present or the list is empty, show it and switch to the README tab.
3. **Track**: form with repo (prefilled), tags, and **Telegram chat ID**, with helper text "Open our Telegram bot, send /start, paste the ID here". List the user's watches (by contact, remembered in `localStorage`, wrapped in try/catch), delete button, and a **Check now** button (this one is for the demo).

## D2 — Quality (P1, 3:30–7:30 AM)
- States for everything: loading skeletons, empty, error by code (`RATE_LIMITED` → friendly "GitHub rate limit hit, try again in a minute", `INVALID_REPO`, `REPO_NOT_FOUND`), network offline.
- **Render all issue/AI text as plain text. Never `dangerouslySetInnerHTML`.** Issue content is untrusted.
- Responsive enough for a phone screen. Keyboard-accessible buttons, visible focus.
- Explain-button results cached in component state so they do not refetch.

## D3 — Polish (P2, after 7:30 AM, only when everything above works)
Nice typography, empty-state illustration, a clear logo/wordmark, a small "how it works" strip on Home.

## D4 — Docs (P0 for README basics by 9:00 AM)
`README.md` must contain (event rule: what, setup, contributing):
- What it is and the problem it solves, in 3 sentences. The pitch: *labels lie, so we check whether an issue is actually safe to start.*
- The architecture diagram from `AGENTS.md`.
- Setup: backend (venv, `pip install -r backend/requirements.txt`, `.env` from `.env.example`, `uvicorn app.main:app --reload`), frontend (`npm install`, `npm run dev`), running tests, running the extension (load unpacked), Telegram bot setup.
- Contributing section (branching, PRs, tests) and a note that the project is read-only toward other people's repos.
- Tech stack and a **Credits** section pointing at `CREDITS.md`, including every AI tool used.
- Honest limitations (rate limits, scoring is heuristic, AI can be wrong).
At **8:30 AM** ask each part owner for 5 lines about their part and fold them in.
`CREDITS.md`: one line per library, API, AI tool, template. Make sure the licence file is present.

`docs/demo-script.md` (2 minutes): problem → paste a real repo → show the ranked "safe to start" list and why a labelled issue got marked `claimed` → Explain an issue → Track the demo repo → run `scripts/demo_create_issue.py` → Check now → Telegram alert on the phone → one line on local AI mode and what comes next. Include a backup plan: a screen recording in case the network or the API fails.

## Deploy
Deploy the frontend (Vercel or similar; check the current free tier). Set `VITE_API_BASE` to the deployed backend URL (Part A gives it to you). Confirm CORS works from the deployed origin.

## Definition of done
- Paste a real repo → ranked issues render with badges, reasons and AI explanations. Track form creates a watch. Every error path shows a friendly message.
- `npm run build` passes. No tokens or secrets in `frontend/`. README and demo script complete.

## Don'ts
- Don't call GitHub from the browser. Don't change the API shapes (ask Part A via the `contract:` process). Don't touch backend code, scoring, AI or the extension.
