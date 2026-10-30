import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = Path(__file__).resolve().parents[1]
if (_ROOT / ".env").is_file():
    load_dotenv(_ROOT / ".env")
if (_BACKEND / ".env").is_file():
    load_dotenv(_BACKEND / ".env")



def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./myopensource.db"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
OLLAMA_URL = os.getenv("OLLAMA_URL") or "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ENABLE_SCHEDULER = _bool("ENABLE_SCHEDULER", False)
ENABLE_TELEGRAM_BOT = _bool("ENABLE_TELEGRAM_BOT", False)
POLL_INTERVAL_SECONDS = _int("POLL_INTERVAL_SECONDS", 10)
DEMO_REPO = os.getenv("DEMO_REPO", "")
DEMO_GITHUB_TOKEN = os.getenv("DEMO_GITHUB_TOKEN", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN") or "http://localhost:5173"
