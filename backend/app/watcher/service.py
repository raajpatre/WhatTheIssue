
"""
backend/app/watcher/service.py — Part C (P0)

Watcher service:
- baseline_repo(repo): marks current issues as seen and stores ETag.
- check_all_now(): polls watched repos and sends alerts for qualifying new issues.
- start_scheduler(): starts APScheduler and Telegram bot thread.
- stop_scheduler(): shuts down background services cleanly.
"""

import logging
import os
import threading
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import crud
from app.github import client as github_client
from app.github.labels import labels_match
from app.scoring import engine as scoring_engine
from app.notify import send as notify_send, format_alert as notify_format_alert
from app.notify.telegram_bot import start_bot_thread

logger = logging.getLogger("myopensource.watcher")

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()
_scheduler_started = False


def _get_issue_id(issue: Any) -> int:
    """Extract issue ID from a Pydantic model or dictionary."""
    if hasattr(issue, "id"):
        return int(issue.id)
    return int(issue["id"])


def _get_issue_labels(issue: Any) -> list[str]:
    """Extract labels from a Pydantic model or dictionary."""
    if hasattr(issue, "labels"):
        return list(issue.labels or [])
    return list(issue.get("labels", []) or [])


def _get_scored_status(scored: Any) -> str:
    """Extract status from ScoredIssue."""
    if hasattr(scored, "status"):
        return str(scored.status)
    return str(scored.get("status", "unclear"))


def _get_scored_issue(scored: Any) -> Any:
    """Extract issue from ScoredIssue."""
    if hasattr(scored, "issue"):
        return scored.issue
    return scored.get("issue", {})


def baseline_repo(repo: str) -> None:
    """
    Mark all currently open issues as seen without sending notifications.
    """
    if not repo:
        return

    logger.info("Establishing initial baseline for %s...", repo)

    try:
        owner, name = repo.split("/", 1)
        issue_ids = []

        for page in range(1, 11):
            resp = github_client._get(
                f"/repos/{owner}/{name}/issues",
                params={
                    "state": "open",
                    "sort": "created",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )

            github_client._raise_for_github(resp)
            batch = resp.json()

            if not isinstance(batch, list):
                raise ValueError("GitHub returned an invalid issues response")

            for item in batch:
                if isinstance(item, dict) and "pull_request" not in item:
                    issue_ids.append(int(item["id"]))

            if len(batch) < 100:
                break

        if issue_ids:
            crud.add_seen_issue_ids(repo, issue_ids)

        logger.info(
            "Baselined %d existing issues for %s.",
            len(issue_ids),
            repo,
        )

    except Exception:
        logger.exception("Failed to baseline repository %s.", repo)

def check_all_now() -> dict[str, int]:
    """
    Check all watched repositories for new issues.

    Returns:
        {"checked": number_of_repositories,
         "notified": number_of_successful_notifications}
    """
    checked_count = 0
    notified_count = 0

    logger.info("Watcher check started.")

    try:
        repos = crud.distinct_watched_repos()
    except Exception:
        logger.exception("Failed to fetch watched repositories.")
        return {"checked": 0, "notified": 0}

    for repo in repos:
        try:
            checked_count += 1

            old_etag = crud.get_etag(repo)
            issues, new_etag = github_client.fetch_new_issues(
                repo,
                old_etag,
            )

            if new_etag:
                crud.set_etag(repo, new_etag)

            seen_ids = set(crud.get_seen_issue_ids(repo) or [])

            fresh = [
                issue
                for issue in (issues or [])
                if _get_issue_id(issue) not in seen_ids
            ]

            if not fresh:
                logger.info("No new issues found in %s.", repo)
                continue

            scored_issues = [
                scoring_engine.score_issue(issue)
                for issue in fresh
            ]

            watches = crud.list_watches(repo=repo) or []

            for watch in watches:
                watch_channel = getattr(watch, "channel", "telegram")
                watch_contact = getattr(watch, "contact", "")
                watch_tags = (
                    getattr(watch, "tags", ["good first issue"])
                    or ["good first issue"]
                )

                for scored in scored_issues:
                    issue_obj = _get_scored_issue(scored)
                    issue_labels = _get_issue_labels(issue_obj)
                    status = _get_scored_status(scored)

                    if (
                        labels_match(issue_labels, watch_tags)
                        and status in ("safe", "unclear")
                    ):
                        alert_message = notify_format_alert(scored)

                        sent = notify_send(
                            watch_channel,
                            watch_contact,
                            alert_message,
                        )

                        if sent:
                            notified_count += 1

            # Mark fresh issues as seen to prevent duplicate alerts.
            fresh_ids = [
                _get_issue_id(issue)
                for issue in fresh
            ]

            crud.add_seen_issue_ids(repo, fresh_ids)

        except Exception:
            logger.exception(
                "Error during watcher check for repository %s.",
                repo,
            )
            continue

    result = {
        "checked": checked_count,
        "notified": notified_count,
    }

    logger.info(
        "Watcher check completed: %d repositories checked, "
        "%d notifications sent.",
        checked_count,
        notified_count,
    )

    return result


def start_scheduler() -> None:
    """
    Start APScheduler and Telegram bot thread.
    Scheduler and bot are controlled by environment flags.
    """
    global _scheduler, _scheduler_started

    with _scheduler_lock:
        if _scheduler_started:
            logger.info("Background services already started in this process.")
            return

        enable_scheduler = (
            os.getenv("ENABLE_SCHEDULER", "0").strip().lower()
            in ("1", "true", "yes")
        )

        try:
            poll_seconds = max(
                1,
                int(
                    os.getenv(
                        "POLL_INTERVAL_SECONDS",
                        "10",
                    ).strip()
                ),
            )
        except ValueError:
            poll_seconds = 10
            logger.warning(
                "Invalid POLL_INTERVAL_SECONDS. Defaulting to 10 seconds."
            )

        if enable_scheduler:
            try:
                _scheduler = BackgroundScheduler(daemon=True)

                _scheduler.add_job(
                    check_all_now,
                    trigger="interval",
                    seconds=poll_seconds,
                    id="myopensource_repo_watcher",
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True,
                )

                _scheduler.start()

                logger.info(
                    "Watcher scheduler started. Poll interval: %d seconds.",
                    poll_seconds,
                )

            except Exception:
                logger.exception("Failed to start APScheduler.")
                _scheduler = None

        else:
            logger.info(
                "Watcher scheduler disabled (ENABLE_SCHEDULER=0)."
            )

        start_bot_thread()
        _scheduler_started = True


def stop_scheduler() -> None:
    """Stop the scheduler and Telegram bot thread cleanly."""
    global _scheduler, _scheduler_started

    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=False)

        _scheduler = None
        _scheduler_started = False

    from app.notify.telegram_bot import stop_bot_thread

    stop_bot_thread()
    logger.info("Watcher background services stopped.")
