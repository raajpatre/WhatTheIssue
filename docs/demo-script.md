# 2-Minute Demo Presentation Script: myOpenSource

> **Target Audience**: Hacktoberfest 2026 Judges & Open-Source Maintainers  
> **Total Time**: 120 seconds  
> **Presenter Persona**: Enthusiastic open-source contributor & builder  
> **Key Message**: *Labels lie. We verify whether an issue is actually safe to start.*

---

## Equipment & Prep Checklist (T-minus 5 minutes)
- [ ] Laptop with browser open to `http://localhost:5173` (or deployed URL).
- [ ] Backend running (`uvicorn app.main:app` or verified online).
- [ ] Phone placed on the podium with Telegram notifications unmuted.
- [ ] Terminal window open on the side ready with: `python3 scripts/demo_create_issue.py`.
- [ ] Backup recording video file queued on desktop in case Wi-Fi drops.

---

## Demo Script (Timeline)

### 0:00 - 0:25 · The Hook & Problem (25s)
> *"Hello everyone! How many of you have ever clicked on a `good first issue` on GitHub, cloned the repo, read the code for 3 hours, only to realize someone already opened a PR three weeks ago or the maintainer never replied?*
>
> *Every beginner faces this. Labels lie! Today we built **myOpenSource** — a system that looks beyond the labels to find issues that are **actually safe to start**."*

### 0:25 - 0:50 · Live Triage: Safe vs. Claimed (25s)
> *(Action: Type or click `demo-org/demo-repo` into the search bar and press **Analyze Repo**.)*
>
> *"Watch what happens when we analyze this repo. Instead of a raw list, we get an instant safety verdict:*
> - *Issue #12 (typo fix) is **Safe to Start** with a score of 95/100. It has no PR collisions and maintainer Jane explicitly commented 'PRs welcome'.*
> - *Look at Issue #15: it has the label `good-first-issue`, but our engine flagged it as **Claimed** (red badge). Why? Because contributor eager-contributor already opened a linked pull request! That saves a new contributor hours of wasted duplicate effort."*

### 0:50 - 1:15 · AI Guidance & README Mining (25s)
> *(Action: Click the **Explain this issue** button on Issue #12.)*
>
> *"Now click 'Explain this issue'. Our AI model doesn't just restate the issue. It gives you:*
> 1. *A 2-sentence summary in plain English.*
> 2. *The exact files to touch (`docs/install.md`).*
> 3. *The beginner rating: 10/10.*
> 4. *Five concrete first steps so you know what to do without being overwhelmed.*
>
> *(Action: Switch to the **From the README** tab.)*
> *And if all issues in a repo are claimed, we scan the project README for starter opportunities like missing Docker quickstarts or docs fixes."*

### 1:15 - 1:45 · The Live Alert: Watcher + Telegram (30s)
> *(Action: Click **Track Repos**, prefilled with `demo-org/demo-repo`. Input the Telegram Chat ID.)*
>
> *"Now the killer feature: watching repos. Let's track `demo-org/demo-repo` with our Telegram chat ID.*
>
> *(Action: In the terminal window, run: `python3 scripts/demo_create_issue.py`.)*
> *Imagine a maintainer just created a brand new issue on GitHub.*
>
> *(Action: In UI, click **Check Now (Demo)**.)*
> *Our scheduler detects the new issue in the background...*
> *(Phone chimes with Telegram push notification! Hold up phone to audience / camera).*
> *Boom! Within seconds, a Telegram notification arrived with the issue title, safety badge, and direct link."*

### 1:45 - 2:00 · Architecture & What's Next (15s)
> *"Everything is powered by FastAPI, SQLite, and dual AI providers: Gemini Flash in the cloud or Ollama for 100% private local inference. We also built a Chrome extension that shows safety badges directly inside GitHub.
>
> myOpenSource makes your first open-source contribution safe, fast, and exciting. Thank you!"*

---

## Contingency & Backup Plan (If Live Network / API Fails)

| Failure Scenario | Instant Mitigation |
|---|---|
| **Wi-Fi disconnects or is slow** | Toggle `VITE_USE_MOCK=1` in `frontend/.env` or run on the preloaded mock server. All data, scores, AI breakdowns, and simulated Telegram triggers run flawlessly offline with zero network required. |
| **GitHub API Rate Limit hit** | Point to the cached issues and mention our built-in ETag conditional caching system (`HTTP 304`), which prevents unnecessary rate consumption. |
| **Complete hardware glitch** | Play `demo-backup-recording.mp4` (saved in `artifacts/demo_video.mp4` and on local desktop), which showcases the full end-to-end flow with voiceover. |
