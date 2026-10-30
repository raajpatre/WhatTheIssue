import httpx
import pytest

from app.github import client as gh
from app.github.exceptions import RateLimitError, RepoNotFoundError


def _issue(
    *,
    issue_id: int,
    number: int,
    title: str,
    labels: list[str],
    pull_request: dict | None = None,
) -> dict:
    item = {
        "id": issue_id,
        "number": number,
        "title": title,
        "body": f"body {number}",
        "html_url": f"https://github.com/acme/widgets/issues/{number}",
        "labels": [{"name": name} for name in labels],
        "assignees": [{"login": "alice"}],
        "comments": 2,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }
    if pull_request is not None:
        item["pull_request"] = pull_request
    return item


@pytest.fixture
def install_client():
    clients: list[httpx.Client] = []

    def _install(handler):
        transport = httpx.MockTransport(handler)
        mock = httpx.Client(transport=transport, timeout=20.0)
        clients.append(mock)
        gh.set_http_client_for_tests(mock)
        return mock

    yield _install
    gh.set_http_client_for_tests(None)


def test_fetch_issues_drops_prs_and_filters_labels_client_side(install_client) -> None:
    seen_params: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/widgets/issues":
            seen_params.append(dict(request.url.params))
            assert "labels" not in request.url.params
            payload = [
                _issue(
                    issue_id=1,
                    number=1,
                    title="A PR",
                    labels=["good first issue"],
                    pull_request={"url": "https://api.github.com/repos/acme/widgets/pulls/1"},
                ),
                _issue(issue_id=2, number=2, title="Good one", labels=["good-first-issue"]),
                _issue(issue_id=3, number=3, title="A bug", labels=["bug"]),
            ]
            return httpx.Response(200, json=payload)
        if path.endswith("/comments") or path.endswith("/timeline"):
            return httpx.Response(200, json=[])
        return httpx.Response(500, json={"message": f"unexpected {path}"})

    install_client(handler)
    issues = gh.fetch_issues("acme/widgets")
    assert [issue.number for issue in issues] == [2]
    assert issues[0].title == "Good one"
    assert issues[0].repo == "acme/widgets"
    assert issues[0].labels == ["good-first-issue"]
    assert all(params.get("state") == "open" for params in seen_params)
    assert all("labels" not in params for params in seen_params)


def test_fetch_new_issues_304_returns_empty_and_same_etag(install_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("If-None-Match") == 'W/"abc"'
        return httpx.Response(304)

    install_client(handler)
    issues, etag = gh.fetch_new_issues("acme/widgets", 'W/"abc"')
    assert issues == []
    assert etag == 'W/"abc"'


def test_fetch_readme_404_returns_empty_string(install_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/acme/widgets/readme"
        assert request.headers.get("Accept") == "application/vnd.github.raw+json"
        return httpx.Response(404, json={"message": "Not Found"})

    install_client(handler)
    assert gh.fetch_readme("acme/widgets") == ""


def test_fetch_issues_404_raises_repo_not_found(install_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    install_client(handler)
    with pytest.raises(RepoNotFoundError):
        gh.fetch_issues("missing/repo")


def test_fetch_issues_429_raises_rate_limit(install_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"X-RateLimit-Remaining": "0"},
            json={"message": "API rate limit exceeded"},
        )

    install_client(handler)
    with pytest.raises(RateLimitError):
        gh.fetch_issues("acme/widgets")
