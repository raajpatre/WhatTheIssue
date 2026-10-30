from fastapi.testclient import TestClient

from app.github.client import parse_repo
from app.github.labels import labels_match, normalize_label
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_repo() -> None:
    assert parse_repo("https://github.com/owner/name") == "owner/name"
    assert parse_repo("https://github.com/owner/name.git") == "owner/name"
    assert parse_repo("https://github.com/owner/name/") == "owner/name"
    assert parse_repo("https://github.com/owner/name/issues") == "owner/name"
    assert parse_repo("owner/name") == "owner/name"


def test_labels_match() -> None:
    assert normalize_label("good-first-issue") == "good first issue"
    assert labels_match(["good-first-issue"], ["good first issue"])
    assert labels_match(["Good First Issue"], ["good_first_issue"])
    assert not labels_match(["bug"], ["good first issue"])
