# Complete Live Deployment Guide

This guide walks you through deploying **WhatTheIssue (myOpenSource)** to production with a live FastAPI backend, React frontend, persistent database, and real-time Telegram watcher.

---

## Architecture Overview

```text
┌────────────────────────┐         ┌────────────────────────┐
│  React + Vite Frontend │ ◄─────► │    FastAPI Backend     │
│  (Vercel / Netlify)    │  CORS   │  (Render / Railway)    │
└────────────────────────┘         └───────────┬────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
     ┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
     │  GitHub REST API │            │   Google Gemini  │            │  PostgreSQL / DB │
     │  (Rate Limit 5k) │            │   (AI Summaries) │            │  (Supabase/Cloud)│
     └──────────────────┘            └──────────────────┘            └──────────────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │   Telegram Bot   │
                                     │  (Issue Alerts)  │
                                     └──────────────────┘
```

---

## 1. Pre-Flight Checklist (API Keys & Secrets)

Before deploying, collect the following credentials:

| Secret / Config | Where to get it | Purpose |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | GitHub -> Settings -> Developer settings -> Personal access tokens (fine-grained or classic with `public_repo`) | Increases rate limits from 60 req/hr to 5,000 req/hr. |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) | Powers AI 3-sentence issue breakdowns and README suggestion summaries. |
| `TELEGRAM_BOT_TOKEN` | Telegram app -> `@BotFather` -> `/newbot` | Sends automated Telegram push alerts when new starter issues are posted. |
| `DATABASE_URL` | [Supabase](https://supabase.com/) (Free PostgreSQL) or SQLite | Stores tracked repos, seen issue IDs, and cached AI insights across redeploys. |

---

## 2. Deploying the Backend (FastAPI on Render)

### Option A: Using the Render Blueprint (`render.yaml`)
1. Push your code to your GitHub repository.
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Blueprint**.
3. Connect your GitHub repository (`WhatTheIssue`).
4. Render will parse `render.yaml` and configure the service automatically.
5. In the prompt, enter your secrets:
   - `GEMINI_API_KEY`
   - `GITHUB_TOKEN`
   - `TELEGRAM_BOT_TOKEN`
   - `DATABASE_URL` (if using Supabase; otherwise default SQLite is used)
6. Click **Apply**.

---

### Option B: Manual Web Service Setup on Render
1. In Render, click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following build & runtime settings:
   - **Name**: `whattheissue-api`
   - **Language / Runtime**: `Python 3`
   - **Region**: Choose closest to you (e.g. Frankfurt, Oregon, Singapore)
   - **Branch**: `main` (or your active release branch)
   - **Build Command**:
     ```bash
     pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
     ```
4. Under **Environment Variables**, add:
   ```ini
   DATABASE_URL=sqlite:///./myopensource.db
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your-gemini-api-key>
   GITHUB_TOKEN=<your-github-token>
   ENABLE_SCHEDULER=1
   ENABLE_TELEGRAM_BOT=1
   TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
   POLL_INTERVAL_MINUTES=10
   ```
   *(Note: If using Supabase PostgreSQL, replace `DATABASE_URL` with your Supabase pooler connection string: `postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`).*
5. Click **Create Web Service**.
6. Once deployed, note down your backend URL (e.g., `https://whattheissue-api.onrender.com`).
7. Verify by visiting `https://whattheissue-api.onrender.com/api/health` in your browser. It should return:
   ```json
   {"status": "ok"}
   ```

---

## 3. Deploying the Frontend (React + Vite on Vercel)

Vercel provides instant static builds with worldwide CDN caching.

1. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New...** -> **Project**.
2. Import your GitHub repository (`WhatTheIssue`).
3. In the project configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click `Edit` and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   ```ini
   VITE_API_BASE=https://whattheissue-api.onrender.com
   VITE_USE_MOCK=0
   ```
   *(Replace with your actual Render backend URL from Step 2).*
5. Click **Deploy**.
6. Vercel will build the frontend in ~30 seconds and provide you with a live URL (e.g. `https://whattheissue.vercel.app`).

---

## 4. Setting up the Live Telegram Bot

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to choose a name and username (e.g., `WhatTheIssueBot`).
3. Copy the token provided by BotFather into your backend `TELEGRAM_BOT_TOKEN` environment variable.
4. Open your new bot in Telegram and press `/start`.
5. The bot will reply with a welcome message and your numeric **Chat ID** (or you can use `@userinfobot` to look up your Chat ID).
6. On your live web app (`https://whattheissue.vercel.app`), go to the **Track Repos** view:
   - Enter a repository (e.g., `pallets/flask`).
   - Enter your Telegram Chat ID in the contact field.
   - Click **Start Tracking**.
7. Click **Check Now** or wait for maintainers to post a new issue. You will receive an instant Telegram message!

> [!WARNING]
> **Single Bot Instance Rule**: Never run more than one backend process with `ENABLE_TELEGRAM_BOT=1` using the same bot token. If multiple instances poll the same token, Telegram will return HTTP `409 Conflict`. If scaling horizontally, enable the Telegram bot on only ONE designated worker instance.

---

## 5. Post-Deployment Verification Checklist

Verify that every feature works end-to-end on your live domain:

- [ ] **Health Check**: `GET https://<your-backend>/api/health` returns `{"status":"ok"}`.
- [ ] **Live Repository Analysis**:
  - Open `https://<your-frontend>`.
  - Enter `pallets/flask` and click **Analyze Repo**.
  - Verify that live issues are fetched, scored (`safe`, `claimed`, `stale`), and displayed without mock warnings.
- [ ] **Live AI Breakdown**:
  - Click on an issue to expand it.
  - Click **Explain with AI**.
  - Verify that a 3-sentence summary, skills needed, and beginner rating are generated by Gemini.
- [ ] **README Suggestions**:
  - Scroll down to the **Ideas From the README** section.
  - Verify that starter ideas are extracted and displayed.
- [ ] **Live Watcher**:
  - Add a watch for your repository with your Telegram Chat ID.
  - Click **Check Now** on the Track view and verify response status `ok`.
