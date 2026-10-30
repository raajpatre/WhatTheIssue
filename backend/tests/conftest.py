"""
backend/tests/conftest.py — Pytest Configuration & Test DB Isolation

Ensures all tests run in an isolated in-memory SQLite database,
preventing unit tests from requiring a live network/Supabase connection.
"""

import pytest
from app import config
from app.db.session import init_db, reset_engine_for_tests


@pytest.fixture(autouse=True)
def isolated_test_db(monkeypatch):
    test_url = "sqlite:///:memory:"
    monkeypatch.setattr(config, "DATABASE_URL", test_url)
    reset_engine_for_tests(test_url)
    init_db()
    yield
    reset_engine_for_tests(test_url)
