# myOpenSource (WhatTheIssue)

> **Labels lie. We check which GitHub issues are *actually* safe to start on, explain them in plain English, and watch repos for fresh opportunities.**

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)
[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026%20Bengaluru-blue.svg)](https://hacktoberfest.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)

---

## What it is and The Problem It Solves

Finding good starter issues in open-source projects is notoriously frustrating for beginners. Maintainers attach `good first issue` or `beginner` labels, but many of those issues are already claimed by other contributors, blocked by open pull requests, stale for months, or too vague to tackle.

**myOpenSource** solves this by evaluating open issues beyond their labels: it analyzes active pull requests, assignee status, and discussion freshness to categorize issues as `safe`, `claimed`, `stale`, or `unclear`. An integrated AI assistant breaks down safe issues into first steps and skills needed, and an automated watcher notifies you via Telegram the moment a genuinely new starter issue appears.

---

## Architecture

```text
 React web ───┐
 Chrome ext ──┼──► FastAPI backend ──► GitHub REST API (read-only)
 Telegram bot ┘      │      │
                     │      └──► LLM provider (Gemini Flash | Ollama local)
                     ▼
                  SQLite  ◄── scheduler polls tracked repos every N min
                     │
                     └──► notify: Telegram
```

---

## Key Features

1. **Safety Triage Scoring**:
   - `safe` (green): Verified open, no active PRs, maintainer welcomes contributions.
   - `claimed` (red): Another contributor already opened a PR or was assigned.
   - `stale` (amber): No updates or maintainer response for months; high risk of codebase divergence.
   - `unclear` (grey): Lacks reproduction steps or requirements.
2. **AI-Powered Issue Breakdown**:
   - Explains issues in <= 3 sentences of plain English.
   - Highlights files to touch and skills needed.
   - Generates up to 5 recommended concrete first steps.
   - Displays a Beginner Friendliness rating (0 to 10).
3. **Ideas From the README**:
   - When labelled issues are scarce, extracts starter documentation, tests, and quickstart setup tasks directly from the project README.
4. **Repository Watcher & Telegram Alerts**:
   - Track repos by label tags (`good first issue`, `help wanted`).
   - Get instant Telegram push notifications whenever maintainers post a new matching issue.
   - "Check Now" button for live demo validation.

---

## Quick Start & Setup

### 1. Prerequisites
- Node.js (v18+) and npm
- Python 3.10+
- (Optional) Telegram account to receive alerts

### 2. Frontend Setup (React + Vite)
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment (default runs with mock data for instant testing)
cp .env.example .env

# Start the Vite development server (runs on http://localhost:5173)
npm run dev

# Or build the production bundle
npm run build
```

> **Mock Mode vs Backend Mode**:
> In `frontend/.env`, set `VITE_USE_MOCK=1` to test the complete UI and simulated AI explanations without running the backend. Set `VITE_USE_MOCK=0` and point `VITE_API_BASE=http://localhost:8000` to connect to the live FastAPI backend.

### 3. Backend Setup (FastAPI)
```bash
# Navigate to root directory
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Create your local environment configuration
cp env.example .env

# Run FastAPI backend (runs on http://localhost:8000)
uvicorn app.main:app --reload
```

### 4. Running Backend Tests
```bash
pytest backend/tests/
```

### 5. Running the Chrome Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked** and select the `extension/` directory.
4. Browse to any GitHub repository to trigger the myOpenSource badge overlay.

### 6. Telegram Bot Setup
1. Message `@BotFather` on Telegram to create a bot and obtain a `TELEGRAM_BOT_TOKEN`.
2. Set `TELEGRAM_BOT_TOKEN` in `.env`.
3. Start the bot by setting `ENABLE_TELEGRAM_BOT=1`.
4. Open your bot in Telegram, send `/start`, and copy your numeric Chat ID into the myOpenSource Track form.

---

## Demo Script

A complete 2-minute walkthrough rehearsed for judges is documented in [`docs/demo-script.md`](file:///Users/raajpatre/Documents/HacktoberFest/WhatTheIssue/docs/demo-script.md).

---

## Contributing

We welcome contributions! Please adhere to our project workflow:
- **Branching**: Work on short-lived branches prefixed with your track (e.g. `d/<feature>` or `fix/<topic>`).
- **Read-Only Guarantee**: **Our application is strictly READ-ONLY toward third-party GitHub repositories.** We never create issues, comments, PRs, reactions, or stars on repositories we don't own.
- **Verification**: Ensure all tests pass (`pytest`) and the frontend bundle compiles cleanly (`npm run build`) before opening pull requests.

---

## Tech Stack

- **Frontend**: React 18, Vite, Vanilla CSS Design System, Lucide React icons
- **Backend**: FastAPI, Pydantic, SQLAlchemy, SQLite, Uvicorn
- **AI & Scoring Providers**: Google Gemini Flash / Ollama Local LLMs
- **Notifications**: Telegram Bot API, APScheduler
- **Extension**: Chrome Manifest V3

---

## Credits & Attributions

Every library, API, dataset, and AI tool used across this project is transparently credited in [`CREDITS.md`](file:///Users/raajpatre/Documents/HacktoberFest/WhatTheIssue/CREDITS.md).

---

## Honest Limitations

1. **GitHub API Rate Limits**: Unauthenticated calls to GitHub are limited to 60 requests/hour per IP. Adding a read-only personal access token (`GITHUB_TOKEN`) increases this to 5,000 requests/hour.
2. **Heuristic Scoring**: Our scoring algorithm accurately detects PR references, assignees, and recency, but cannot guarantee maintainer response latency.
3. **AI Explanations**: LLM-generated summaries and first steps provide helpful starting guidance, but contributors should always review repo-specific `CONTRIBUTING.md` guidelines before opening a pull request.
