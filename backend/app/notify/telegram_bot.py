"""
backend/app/notify/telegram_bot.py — Part C (P0)

Telegram Bot long-polling daemon.
Gated by ENABLE_TELEGRAM_BOT=1.
Commands supported:
- /start: returns user chat ID & instructions
- /track owner/repo [tag1,tag2]: creates a watch and baselines the repo
- /list: lists active watches for this chat ID
- /untrack <id>: removes a watch by ID
"""

import html
import logging
import os
import re
import threading
import time
from typing import Any
import httpx
try:
    from app.notify.telegram import send_telegram_message, mask_token
except ImportError:
    try:
        from backend.app.notify.telegram import send_telegram_message, mask_token
    except ImportError:
        from .telegram import send_telegram_message, mask_token

logger = logging.getLogger("myopensource.notify.bot")

# Optional imports for Part A contract integration
try:
    from app.db import crud
    from app.schemas import WatchIn
except ImportError:
    # NEEDS-FROM-PART-A: app.db.crud, app.schemas.WatchIn
    crud = None
    WatchIn = None


_bot_thread: threading.Thread | None = None
_stop_event = threading.Event()


def parse_track_command(args_text: str) -> tuple[str, list[str]]:
    """
    Parse arguments of /track command.
    Format: owner/repo [tag1,tag2] or owner/repo tag1, tag2
    """
    parts = args_text.strip().split(maxsplit=1)
    if not parts:
        raise ValueError("Missing repository. Usage: /track owner/repo [tag1,tag2]")

    repo = parts[0].strip().strip("/").lower()
    # Normalize repo: remove https://github.com/ prefix if user pasted full URL
    if "github.com/" in repo:
        repo = repo.split("github.com/")[-1].strip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]

    # Validate repo format: owner/name
    if not re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", repo):
        raise ValueError(f"Invalid repository format '{repo}'. Expected 'owner/repo'.")

    tags = ["good first issue"]
    if len(parts) > 1 and parts[1].strip():
        raw_tags = parts[1].strip()
        # Handle optional bracket syntax: [tag1, tag2]
        if raw_tags.startswith("[") and raw_tags.endswith("]"):
            raw_tags = raw_tags[1:-1]
        custom_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        if custom_tags:
            tags = custom_tags

    return repo, tags


def handle_message(chat_id: str, text: str) -> None:
    """Handle incoming Telegram messages and execute commands."""
    clean_text = text.strip()
    if not clean_text:
        return

    # Extract command and arguments
    parts = clean_text.split(maxsplit=1)
    cmd = parts[0].lower()
    # Handle bot command syntax like /start@mybot
    if "@" in cmd:
        cmd = cmd.split("@")[0]
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/help"):
        msg = (
            "👋 <b>Welcome to myOpenSource Bot!</b>\n\n"
            f"Your Telegram Chat ID: <code>{chat_id}</code>\n"
            "<i>(Copy this Chat ID into the myOpenSource web app or extension to receive instant alerts here!)</i>\n\n"
            "<b>Commands:</b>\n"
            "• <code>/track owner/repo [tags]</code> — Watch a repository (default tags: <code>good first issue</code>)\n"
            "• <code>/list</code> — View your active repository watches\n"
            "• <code>/untrack &lt;id&gt;</code> — Remove an active watch by its ID"
        )
        send_telegram_message(chat_id, msg)
        return

    if cmd == "/track":
        if not args:
            send_telegram_message(
                chat_id,
                "⚠️ <b>Usage:</b> <code>/track owner/repo [tag1,tag2]</code>\n"
                "Example: <code>/track facebook/react good first issue</code>",
            )
            return

        try:
            repo, tags = parse_track_command(args)
        except ValueError as e:
            send_telegram_message(chat_id, f"⚠️ {html.escape(str(e))}")
            return

        if crud is None or WatchIn is None:
            logger.error("Database CRUD layer not available yet; cannot save watch.")
            send_telegram_message(
                chat_id,
                "❌ Backend database is currently initializing. Please try again shortly.",
            )
            return

        try:
            watch_obj = WatchIn(
                repo=repo,
                tags=tags,
                channel="telegram",
                contact=chat_id,
            )
            created_watch = crud.create_watch(watch_obj)

            # Establish baseline so existing issues aren't flooded
            try:
                from app.watcher.service import baseline_repo
                baseline_repo(repo)
            except Exception as be:
                logger.warning("Baseline warning for repo %s: %s", repo, be)

            tags_display = ", ".join(created_watch.tags)
            resp = (
                f"✅ <b>Successfully watching {html.escape(repo)}!</b> (Watch ID: <code>{created_watch.id}</code>)\n"
                f"Tags: <code>{html.escape(tags_display)}</code>\n\n"
                "Existing issues have been recorded as baseline. You'll receive a Telegram alert as soon as a new beginner-friendly issue appears!"
            )
            send_telegram_message(chat_id, resp)
        except Exception as e:
            logger.error("Error creating watch for %s: %s", repo, e)
            send_telegram_message(chat_id, f"❌ Failed to track repository: {html.escape(str(e))}")
        return

    if cmd == "/list":
        if crud is None:
            send_telegram_message(chat_id, "❌ Backend database is currently initializing.")
            return

        try:
            watches = crud.list_watches(contact=chat_id)
            if not watches:
                send_telegram_message(
                    chat_id,
                    "ℹ️ You have no active watches.\n"
                    "Use <code>/track owner/repo</code> to start watching a repository!",
                )
                return

            lines = ["📋 <b>Your Active Watches:</b>\n"]
            for w in watches:
                tags_str = ", ".join(getattr(w, "tags", []))
                lines.append(
                    f"• <b>#{w.id}</b>: <code>{html.escape(w.repo)}</code> (tags: <code>{html.escape(tags_str)}</code>)"
                )
            lines.append("\nUse <code>/untrack &lt;id&gt;</code> to stop watching a repository.")
            send_telegram_message(chat_id, "\n".join(lines))
        except Exception as e:
            logger.error("Error listing watches: %s", e)
            send_telegram_message(chat_id, "❌ Failed to retrieve your watches.")
        return

    if cmd == "/untrack":
        if not args:
            send_telegram_message(chat_id, "⚠️ <b>Usage:</b> <code>/untrack &lt;id&gt;</code>\nExample: <code>/untrack 3</code>")
            return

        try:
            watch_id = int(args.strip())
        except ValueError:
            send_telegram_message(chat_id, "⚠️ Invalid watch ID. Must be an integer number.")
            return

        if crud is None:
            send_telegram_message(chat_id, "❌ Backend database is currently initializing.")
            return

        try:
            deleted = crud.delete_watch(watch_id)
            if deleted:
                send_telegram_message(chat_id, f"✅ Successfully removed watch <b>#{watch_id}</b>.")
            else:
                send_telegram_message(chat_id, f"❌ Watch <b>#{watch_id}</b> not found.")
        except Exception as e:
            logger.error("Error deleting watch %d: %s", watch_id, e)
            send_telegram_message(chat_id, f"❌ Failed to remove watch #{watch_id}.")
        return

    # Unrecognized command
    send_telegram_message(
        chat_id,
        "❓ Unknown command.\nAvailable commands: <code>/start</code>, <code>/track</code>, <code>/list</code>, <code>/untrack</code>",
    )


def poll_updates_loop(stop_event: threading.Event) -> None:
    """Long polling loop for Telegram Bot getUpdates."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("ENABLE_TELEGRAM_BOT is active but TELEGRAM_BOT_TOKEN is empty. Poller exiting.")
        return

    logger.info("Starting Telegram bot long-polling with token %s...", mask_token(token))
    offset = 0

    while not stop_event.is_set():
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {
            "offset": offset,
            "timeout": 15,
            "allowed_updates": ["message"],
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.get(url, params=params)

                if resp.status_code == 409:
                    logger.error(
                        "Telegram Bot 409 Conflict: Another process is polling this token (%s). Retrying in 10s...",
                        mask_token(token),
                    )
                    time.sleep(10)
                    continue

                if resp.status_code != 200:
                    logger.error("Telegram getUpdates returned status %d. Retrying in 5s...", resp.status_code)
                    time.sleep(5)
                    continue

                data = resp.json()
                if not data.get("ok"):
                    logger.error("Telegram getUpdates error: %s", data.get("description", "Unknown"))
                    time.sleep(5)
                    continue

                updates = data.get("result", [])
                for upd in updates:
                    update_id = upd.get("update_id", 0)
                    offset = max(offset, update_id + 1)

                    message = upd.get("message")
                    if message and "text" in message:
                        chat = message.get("chat", {})
                        chat_id = str(chat.get("id", ""))
                        text = message.get("text", "")
                        if chat_id and text:
                            try:
                                handle_message(chat_id, text)
                            except Exception as handle_exc:
                                logger.error("Error handling Telegram message: %s", handle_exc)

        except (httpx.TimeoutException, httpx.RequestError) as net_err:
            # Expected on network hiccup / timeout during long poll
            time.sleep(2)
        except Exception as e:
            logger.error("Unexpected error in Telegram polling loop: %s", e)
            time.sleep(5)


def start_bot_thread() -> None:
    """Start background daemon thread for Telegram bot polling if enabled."""
    global _bot_thread, _stop_event

    enabled = os.getenv("ENABLE_TELEGRAM_BOT", "0").strip().lower() in ("1", "true", "yes")
    if not enabled:
        logger.info("Telegram bot polling is disabled (ENABLE_TELEGRAM_BOT=0).")
        return

    if _bot_thread and _bot_thread.is_alive():
        logger.info("Telegram bot polling thread is already running.")
        return

    _stop_event.clear()
    _bot_thread = threading.Thread(
        target=poll_updates_loop,
        args=(_stop_event,),
        daemon=True,
        name="telegram-bot-poller",
    )
    _bot_thread.start()
    logger.info("Telegram bot polling thread launched.")


def stop_bot_thread() -> None:
    """Signal Telegram bot poller thread to stop."""
    global _bot_thread, _stop_event
    _stop_event.set()
    if _bot_thread and _bot_thread.is_alive():
        _bot_thread.join(timeout=2.0)
        _bot_thread = None
