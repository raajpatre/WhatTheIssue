#!/usr/bin/env python3
"""
scripts/test_db_connection.py — Database connectivity and table verification.

Tests connection to the configured DATABASE_URL (Supabase PostgreSQL or SQLite)
and verifies that all tables are created properly.
Never logs passwords or tokens.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")
load_dotenv(project_root / "backend" / ".env")

# Ensure backend is on sys.path
sys.path.insert(0, str(project_root / "backend"))

from app import config
from app.db.session import init_db, get_engine
from sqlalchemy import inspect


def mask_db_url(url: str) -> str:
    """Mask credentials in database URL for safe logging."""
    if not url:
        return "[EMPTY]"
    if "@" in url and "://" in url:
        prefix, _, rest = url.partition("://")
        creds, _, host = rest.partition("@")
        user = creds.split(":")[0] if ":" in creds else creds
        return f"{prefix}://{user}:[HIDDEN]@{host}"
    return url


def main() -> None:
    db_url = config.DATABASE_URL
    print(f"🔍 Testing connection to: {mask_db_url(db_url)}")

    try:
        init_db()
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("✅ Database connection successful!")
        print(f"📋 Verified tables ({len(tables)}): {', '.join(sorted(tables))}")
    except Exception as exc:
        print(f"❌ Database connection failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
