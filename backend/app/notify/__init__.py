"""
backend/app/notify/__init__.py — Part C (P0)

Notification dispatch and alert formatting.
Contract:
- send(channel: str, contact: str, text: str) -> bool
- format_alert(s: ScoredIssue) -> str
"""

import html
import logging
from typing import Any

from app.schemas import ScoredIssue

try:
    from app.notify.telegram import send_telegram_message
except ImportError:
    try:
        from backend.app.notify.telegram import send_telegram_message
    except ImportError:
        from .telegram import send_telegram_message

logger = logging.getLogger("myopensource.notify")


def send(channel: str, contact: str, text: str) -> bool:
    """
    Send notification to recipient over specified channel.
    Guaranteed to never raise an exception.
    """
    try:
        norm_channel = (channel or "").strip().lower()
        if norm_channel == "telegram":
            return send_telegram_message(
                chat_id=str(contact).strip(),
                text=text,
            )
        elif norm_channel == "email":
            # P2: Email channel is skipped for hackathon MVP
            logger.info(
                "Email notification skipped (P2). Contact: %s",
                contact,
            )
            return False
        else:
            logger.warning("Unsupported notification channel: %s", channel)
            return False
    except Exception as exc:
        logger.error(
            "Failed to send notification via channel %s: %s",
            channel,
            str(exc),
        )
        return False


def format_alert(s: ScoredIssue | Any) -> str:
    """
    Format a scored issue alert for notifications.
    Includes repo, title, status + score, up to 2 reasons, and issue link.
    Short, readable, and HTML-escaped for Telegram.
    """
    try:
        issue = getattr(s, "issue", None)
        if issue is None and isinstance(s, dict):
            issue = s.get("issue", {})

        def get_val(obj: Any, key: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        repo = str(get_val(issue, "repo", "unknown/repo"))
        title = str(get_val(issue, "title", "Untitled Issue"))
        url = str(get_val(issue, "url", ""))
        status = str(get_val(s, "status", "safe")).upper()
        score = get_val(s, "score", 0)
        reasons_list = get_val(s, "reasons", []) or []
        reasons = [str(r) for r in reasons_list[:2]]

        safe_repo = html.escape(repo)
        safe_title = html.escape(title)
        safe_status = html.escape(status)
        safe_score = html.escape(str(score))
        safe_url = html.escape(url)

        reasons_block = ""
        if reasons:
            reasons_lines = "\n".join(
                f"• {html.escape(r)}" for r in reasons
            )
            reasons_block = (
                f"\n<b>Why beginner-friendly:</b>\n{reasons_lines}\n"
            )

        alert = (
            f"🔔 <b>New Issue in {safe_repo}</b>\n\n"
            f"<b>Title:</b> {safe_title}\n"
            f"<b>Status:</b> {safe_status} (Score: {safe_score}/100)\n"
            f"{reasons_block}\n"
            f"🔗 <a href=\"{safe_url}\">{safe_url}</a>"
        )
        return alert

    except Exception as exc:
        logger.error("Error formatting alert: %s", str(exc))
        # Plain fallback
        return f"🔔 New issue in repository: {getattr(s, 'issue', '')}"
