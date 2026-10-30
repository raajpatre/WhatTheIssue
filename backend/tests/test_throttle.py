from fastapi.testclient import TestClient

from app.api import throttle as throttle_mod
from app.db.session import init_db
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    throttle_mod.reset_throttle_for_tests()
    init_db()


def teardown_function() -> None:
    throttle_mod.reset_throttle_for_tests()


def test_health_is_not_throttled(monkeypatch) -> None:
    monkeypatch.setattr(throttle_mod, "MAX_REQUESTS", 1)
    throttle_mod.reset_throttle_for_tests()
    first = client.get("/api/health")
    second = client.get("/api/health")
    assert first.status_code == 200
    assert second.status_code == 200


def test_per_ip_throttle_returns_rate_limited(monkeypatch) -> None:
    monkeypatch.setattr(throttle_mod, "MAX_REQUESTS", 2)
    throttle_mod.reset_throttle_for_tests()
    assert client.get("/api/watch").status_code == 200
    assert client.get("/api/watch").status_code == 200
    blocked = client.get("/api/watch")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "message" in body["error"]
