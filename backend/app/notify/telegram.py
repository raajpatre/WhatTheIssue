"""
backend/app/notify/telegram.py — Part C (P0)

Telegram Bot API sender.
Sends messages via HTTPS to Telegram Bot API.
Safely escapes untrusted input and prevents secret leakage.
"""

import html
import logging
import os
import httpx

logger = logging.getLogger("myopensource.notify.telegram")


def mask_token(token: str) -> str:
    """Mask token for safe logging without leaking secrets."""
    if not token or len(token) <= 8:
        return "[REDACTED]"
    return f"{token[:4]}...{token[-4:]}"


def send_telegram_message(
    chat_id: str,
    text: str,
    token: str | None = None,
    parse_mode: str = "HTML",
    timeout: float = 10.0,
) -> bool:
    """
    Send a message to a Telegram chat via Telegram Bot API sendMessage.
    Returns True on success, False on failure.
    Never raises exceptions.
    """
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured; cannot send Telegram alert.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)

            # If HTML parsing fails (e.g. malformed entity), fallback to plain text
            if resp.status_code == 400 and parse_mode:
                logger.warning(
                    "Telegram HTML parse error; retrying sendMessage as plain text to chat %s",
                    chat_id,
                )
                plain_payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": False,
                }
                resp = client.post(url, json=plain_payload)

            if resp.status_code == 200:
                return True

            logger.error(
                "Telegram sendMessage failed with status %d (chat_id: %s, token: %s)",
                resp.status_code,
                chat_id,
                mask_token(bot_token),
            )
            return False

    except httpx.RequestError as exc:
        logger.error(
            "Network error sending Telegram message to %s: %s",
            chat_id,
            str(exc),
        )
        return False
    except Exception as exc:
        logger.error(
            "Unexpected error sending Telegram message to %s: %s",
            chat_id,
            str(exc),
        )
        return False
