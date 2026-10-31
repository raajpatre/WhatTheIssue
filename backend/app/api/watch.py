import html
from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.api.errors import AppError
from app.db import crud
from app.github.client import parse_repo
from app.notify import send as notify_send
from app.schemas import Watch, WatchIn
from app.watcher.service import baseline_repo, check_all_now

router = APIRouter()


class TestNotifyIn(BaseModel):
    contact: str
    channel: str = "telegram"


@router.post("/watch")
async def create_watch(body: WatchIn) -> Watch:
    normalized = body.model_copy(update={"repo": parse_repo(body.repo)})
    watch = crud.create_watch(normalized)
    await run_in_threadpool(baseline_repo, watch.repo)

    # If Telegram channel, send an activation confirmation if configured
    if watch.channel == "telegram" and watch.contact:
        tags_str = ", ".join(watch.tags) if watch.tags else "good first issue"
        welcome_text = (
            f"🔔 <b>myOpenSource Watcher Activated!</b>\n\n"
            f"You are now tracking <code>{html.escape(watch.repo)}</code>.\n"
            f"<b>Tags:</b> <code>{html.escape(tags_str)}</code>\n"
            f"<b>Watch ID:</b> <code>#{watch.id}</code>\n\n"
            "Existing issues have been recorded as baseline. You will receive an alert here as soon as a new beginner-friendly issue appears!"
        )
        await run_in_threadpool(notify_send, watch.channel, watch.contact, welcome_text)

    return watch


@router.get("/watch")
async def list_watches(contact: str | None = Query(default=None)) -> list[Watch]:
    return crud.list_watches(contact=contact)


@router.get("/watch/status")
async def watch_status() -> dict:
    """Return watcher scheduler and Telegram bot status."""
    from app import config
    from app.notify.telegram_bot import _bot_thread
    from app.watcher.service import _scheduler

    scheduler_running = bool(_scheduler and _scheduler.running)
    bot_running = bool(_bot_thread and _bot_thread.is_alive())
    watched_repos = crud.distinct_watched_repos()

    return {
        "status": "ok",
        "scheduler": {
            "enabled": config.ENABLE_SCHEDULER,
            "running": scheduler_running,
            "poll_interval_seconds": config.POLL_INTERVAL_SECONDS,
        },
        "bot": {
            "enabled": config.ENABLE_TELEGRAM_BOT,
            "running": bot_running,
            "token_configured": bool(config.TELEGRAM_BOT_TOKEN),
        },
        "watched_repos_count": len(watched_repos),
        "watched_repos": watched_repos,
    }


@router.post("/watch/check-now")
async def watch_check_now() -> dict:
    return await run_in_threadpool(check_all_now)


@router.post("/watch/test-notify")
async def test_notify(body: TestNotifyIn) -> dict:
    """Send a test message to verify the user's notification channel."""
    clean_contact = str(body.contact).strip()
    if not clean_contact:
        raise AppError("INVALID_CONTACT", "Contact (chat ID) is required.", status_code=400)

    test_message = (
        "🔔 <b>myOpenSource Notification Test</b>\n\n"
        "Your alert channel is successfully connected! You will receive real-time alerts "
        "here when beginner-friendly issues appear in your tracked repositories."
    )
    sent = await run_in_threadpool(notify_send, body.channel, clean_contact, test_message)
    return {
        "ok": sent,
        "sent": sent,
        "message": (
            "Notification dispatched to Telegram."
            if sent
            else "Could not send test message. Ensure you started the bot (/start) and TELEGRAM_BOT_TOKEN is set in backend."
        ),
    }


@router.delete("/watch/{id}")
async def delete_watch(id: int) -> dict:
    crud.delete_watch(id)
    return {"ok": True}

