"""SQLAlchemy engine/session helpers.

Engine is created lazily from ``app.config.DATABASE_URL``. Tests that need an
isolated database should monkeypatch ``app.config.DATABASE_URL`` and call
``reset_engine_for_tests(url)`` then ``init_db()``. ``get_engine()`` also
rebuilds if the configured URL changes, so leftover process-global engines are
not reused after a test restores the original URL.
"""

from __future__ import annotations

import threading

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.db.models import Base

_lock = threading.Lock()
_engine: Engine | None = None
_engine_url: str | None = None
_SessionLocal: sessionmaker | None = None


import re
from urllib.parse import parse_qs, quote_plus, urlencode, urlsplit, urlunsplit


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def _is_memory(url: str) -> bool:
    return ":memory:" in url


def _make_engine(url: str) -> Engine:
    kwargs: dict = {}
    if _is_sqlite(url):
        kwargs["connect_args"] = {"check_same_thread": False}
        if _is_memory(url):
            kwargs["poolclass"] = StaticPool
    elif "postgres" in url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        m = re.match(
            r"^(?P<proto>[a-zA-Z0-9+]+://)(?P<user>[^:]+):\[(?P<password>.+)\]@(?P<host>[^@/:]+)(?P<rest>.*)$",
            url,
        )
        if m:
            clean_pwd = quote_plus(m.group("password"))
            url = (
                f"{m.group('proto')}{m.group('user')}:{clean_pwd}@"
                f"{m.group('host')}{m.group('rest')}"
            )
        parsed = urlsplit(url)
        if parsed.query:
            params = parse_qs(parsed.query)
            schema = params.pop("schema", None)
            new_query = urlencode(params, doseq=True)
            url = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment)
            )
            if schema:
                kwargs.setdefault("connect_args", {})["options"] = f"-c search_path={schema[0]}"
    engine = create_engine(url, **kwargs)
    if _is_sqlite(url):

        @event.listens_for(engine, "connect")
        def _enable_wal(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine, _engine_url, _SessionLocal
    url = config.DATABASE_URL
    if _engine is not None and _engine_url == url:
        return _engine
    with _lock:
        url = config.DATABASE_URL
        if _engine is None or _engine_url != url:
            if _engine is not None:
                _engine.dispose()
            _engine = _make_engine(url)
            _engine_url = url
            _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_sessionmaker() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_session() -> Session:
    return get_sessionmaker()()


def reset_engine_for_tests(url: str) -> None:
    """Dispose and rebuild the engine for ``url``.

    Tests should monkeypatch ``app.config.DATABASE_URL`` to a temp sqlite file
    (or ``sqlite:///:memory:``) and pass that same url here, then call
    ``init_db()``. Do not rely on leftover in-memory dicts from older CRUD.
    """
    global _engine, _engine_url, _SessionLocal
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = _make_engine(url)
        _engine_url = url
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
