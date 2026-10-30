from fastapi.testclient import TestClient

from app.api.throttle import reset_throttle_for_tests
from app.db.session import init_db
from app.github.exceptions import RateLimitError, RepoNotFoundError
from app.main import app
from app.schemas import Issue, ReadmeSuggestion

client = TestClient(app)


def setup_function() -> None:
    reset_throttle_for_tests()
    init_db()

_ISSUE = Issue(
    id=101,
    repo="acme/widgets",
    number=12,
    title="Fix typo",
    body="A beginner-friendly docs fix in README.md with steps to reproduce.",
    url="https://github.com/acme/widgets/issues/12",
    labels=["good first issue"],
    created_at="2026-10-01T00:00:00Z",
    updated_at="2026-10-01T00:00:00Z",
)


def test_health_shape() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_repo_shape() -> None:
    response = client.post("/api/repos", json={"url": "not-a-repo"})
    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == "INVALID_REPO"
    assert "message" in body["error"]


def test_post_repos_shape(monkeypatch) -> None:
    monkeypatch.setattr("app.api.repos.fetch_issues", lambda repo, tags=None, limit=30: [_ISSUE])
    response = client.post("/api/repos", json={"url": "https://github.com/acme/widgets"})
    assert response.status_code == 200
    body = response.json()
    assert body["repo"] == "acme/widgets"
    assert body["note"] is None
    assert isinstance(body["issues"], list)
    scored = body["issues"][0]
    assert scored["issue"]["number"] == 12
    assert 0 <= scored["score"] <= 100
    assert scored["status"] in {"safe", "claimed", "stale", "unclear"}
    assert "reasons" in scored


def test_post_repos_empty_sets_note(monkeypatch) -> None:
    monkeypatch.setattr("app.api.repos.fetch_issues", lambda repo, tags=None, limit=30: [])
    response = client.post("/api/repos", json={"url": "acme/empty", "tags": ["good first issue"]})
    assert response.status_code == 200
    body = response.json()
    assert body["repo"] == "acme/empty"
    assert body["issues"] == []
    assert body["note"] == "No issues matched these labels. Try the README suggestions."


def test_list_issues_status_filter(monkeypatch) -> None:
    monkeypatch.setattr("app.api.repos.fetch_issues", lambda repo, tags=None, limit=30: [_ISSUE])
    ok = client.get("/api/repos/acme/listed/issues")
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)
    status = ok.json()[0]["status"]
    assert status in {"safe", "claimed", "stale", "unclear"}
    other = "claimed" if status != "claimed" else "stale"
    none = client.get("/api/repos/acme/listed/issues", params={"status": other})
    assert none.status_code == 200
    assert none.json() == []


def test_suggestions_shape(monkeypatch) -> None:
    monkeypatch.setattr("app.api.repos.fetch_readme", lambda repo: "# widgets")
    monkeypatch.setattr(
        "app.api.repos.ai.suggest_from_readme",
        lambda repo, readme: [
            ReadmeSuggestion(
                title="Add a setup example",
                description="Document one local run command.",
                area="docs",
                why_beginner_friendly="Docs-only change with a clear file to edit.",
            )
        ],
    )
    response = client.get("/api/repos/acme/suggests/suggestions")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["area"] in {"docs", "tests", "bugfix", "feature", "setup", "other"}
    assert "title" in body[0]
    assert "why_beginner_friendly" in body[0]


def test_explain_shape(monkeypatch) -> None:
    monkeypatch.setattr("app.api.issues.fetch_issues", lambda repo, tags=None, limit=30: [_ISSUE])
    response = client.get("/api/issues/acme/widgets/12/explain")
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "beginner_rating" in body
    assert "files_to_touch" in body
    assert "first_steps" in body
    assert "provider" in body


def test_watch_crud_and_check_now() -> None:
    created = client.post(
        "/api/watch",
        json={"repo": "acme/widgets", "tags": ["good first issue"], "channel": "telegram", "contact": "99"},
    )
    assert created.status_code == 200
    watch = created.json()
    assert watch["repo"] == "acme/widgets"
    assert watch["contact"] == "99"
    assert isinstance(watch["id"], int)
    assert watch["created_at"].endswith("Z")

    listed = client.get("/api/watch", params={"contact": "99"})
    assert listed.status_code == 200
    assert any(item["id"] == watch["id"] for item in listed.json())

    check = client.post("/api/watch/check-now")
    assert check.json()["notified"] == 0
    assert check.json()["checked"] in (0, 1)

    deleted = client.delete(f"/api/watch/{watch['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_repo_not_found_shape(monkeypatch) -> None:
    def _raise(repo, tags=None, limit=30):
        raise RepoNotFoundError("Repository not found")

    monkeypatch.setattr("app.api.repos.fetch_issues", _raise)
    response = client.post("/api/repos", json={"url": "missing/repo"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REPO_NOT_FOUND"


def test_github_rate_limited_shape(monkeypatch) -> None:
    def _raise(repo, tags=None, limit=30):
        raise RateLimitError("GitHub rate limit hit, try again in a minute")

    monkeypatch.setattr("app.api.repos.fetch_issues", _raise)
    response = client.post("/api/repos", json={"url": "acme/widgets"})
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "try again" in body["error"]["message"].lower()
