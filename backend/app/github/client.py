import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import httpx

from app import config
from app.github.exceptions import RateLimitError, RepoNotFoundError, UpstreamError
from app.github.labels import labels_match
from app.schemas import Comment, Issue

DEFAULT_TAGS = ["good first issue"]
_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")

API_BASE = "https://api.github.com"
# VERIFY: https://docs.github.com/en/rest/about-the-rest-api/api-versions
# GitHub currently documents 2022-11-28 (supported until 2028-03-10) and a newer
# 2026-03-10 version. We pin 2022-11-28 as specified; requests without the header
# also default to 2022-11-28.
GITHUB_API_VERSION = "2022-11-28"
_TIMEOUT = 20.0
_ENRICH_WORKERS = 8

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: httpx.Client | None = None


def parse_repo(url_or_slug: str) -> str:
    raw = (url_or_slug or "").strip()
    if not raw:
        raise ValueError("repository is empty")

    lowered = raw.lower()
    looks_url = (
        "://" in raw
        or lowered.startswith("github.com/")
        or lowered.startswith("www.github.com/")
    )
    if looks_url:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = parsed.netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if host != "github.com":
            raise ValueError(f"not a GitHub repository: {url_or_slug}")
        path = parsed.path
    else:
        path = raw

    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"not a GitHub repository: {url_or_slug}")
    owner, name = parts[0], parts[1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    if not _SEGMENT.fullmatch(owner) or not _SEGMENT.fullmatch(name):
        raise ValueError(f"not a GitHub repository: {url_or_slug}")
    return f"{owner}/{name}"


def _http() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(timeout=_TIMEOUT)
        return _client


def close_http_client() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None


def set_http_client_for_tests(client: httpx.Client | None) -> None:
    """Replace the shared httpx client. Tests inject a MockTransport client here."""
    global _client
    with _client_lock:
        if _client is not None and _client is not client:
            try:
                _client.close()
            except Exception:
                pass
        _client = client


def _headers(accept: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": accept or "application/vnd.github+json",
        "User-Agent": "myopensource",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    token = (config.GITHUB_TOKEN or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _split_repo(repo: str) -> tuple[str, str]:
    owner, sep, name = repo.partition("/")
    if not sep or not owner or not name or "/" in name:
        raise ValueError(f"not a GitHub repository: {repo}")
    return owner, name


def _raise_for_github(resp: httpx.Response, *, allow_304: bool = False) -> None:
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        logger.info("GitHub rate-limit remaining=%s", remaining)

    if resp.status_code == 304 and allow_304:
        return
    if resp.status_code == 404:
        raise RepoNotFoundError("Repository not found")
    remaining_zero = remaining is not None and remaining.strip() == "0"
    if remaining_zero or resp.status_code in (403, 429):
        raise RateLimitError("GitHub rate limit exceeded")
    if resp.status_code >= 400:
        raise UpstreamError(f"GitHub returned HTTP {resp.status_code}")


def _get(
    path: str,
    *,
    params: dict | None = None,
    extra_headers: dict[str, str] | None = None,
    accept: str | None = None,
) -> httpx.Response:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    headers = _headers(accept=accept)
    if extra_headers:
        headers.update(extra_headers)
    try:
        return _http().get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise UpstreamError("GitHub request failed") from exc


def _label_names(item: dict) -> list[str]:
    names: list[str] = []
    for label in item.get("labels") or []:
        if isinstance(label, dict) and label.get("name"):
            names.append(str(label["name"]))
        elif isinstance(label, str):
            names.append(label)
    return names


def _assignee_logins(item: dict) -> list[str]:
    logins: list[str] = []
    for assignee in item.get("assignees") or []:
        if isinstance(assignee, dict) and assignee.get("login"):
            logins.append(str(assignee["login"]))
    return logins


def _issue_from_json(
    item: dict,
    repo: str,
    *,
    comments: list[Comment] | None = None,
    linked_pr_open: bool = False,
) -> Issue:
    return Issue(
        id=int(item["id"]),
        repo=repo,
        number=int(item["number"]),
        title=item.get("title") or "",
        body=item.get("body") or "",
        url=item.get("html_url") or "",
        labels=_label_names(item),
        assignees=_assignee_logins(item),
        comments_count=int(item.get("comments") or 0),
        comments=comments or [],
        linked_pr_open=linked_pr_open,
        created_at=item.get("created_at") or "",
        updated_at=item.get("updated_at") or "",
    )


def _fetch_comments(owner: str, name: str, number: int) -> list[Comment]:
    try:
        resp = _get(
            f"/repos/{owner}/{name}/issues/{number}/comments",
            params={"per_page": 100},
        )
        _raise_for_github(resp)
        data = resp.json()
        if not isinstance(data, list):
            return []
        mapped: list[Comment] = []
        for item in data[-10:]:
            if not isinstance(item, dict):
                continue
            user = item.get("user")
            login = user.get("login") if isinstance(user, dict) else None
            mapped.append(
                Comment(
                    author=str(login) if login else "ghost",
                    body=item.get("body") or "",
                    created_at=item.get("created_at") or "",
                    author_association=item.get("author_association") or "NONE",
                )
            )
        return mapped
    except Exception:
        logger.warning("comments fetch failed for %s/%s#%s", owner, name, number)
        return []


def _linked_pr_open(owner: str, name: str, number: int) -> bool:
    # VERIFY: https://docs.github.com/en/rest/issues/timeline and
    # https://docs.github.com/en/rest/using-the-rest-api/issue-event-types
    # cross-referenced events expose source.issue; a PR is indicated by a
    # pull_request key on source.issue, and source.issue.state is "open"/"closed".
    try:
        resp = _get(
            f"/repos/{owner}/{name}/issues/{number}/timeline",
            params={"per_page": 100},
        )
        _raise_for_github(resp)
        events = resp.json()
        if not isinstance(events, list):
            return False
        for event in events:
            if not isinstance(event, dict) or event.get("event") != "cross-referenced":
                continue
            source = event.get("source") or {}
            issue = source.get("issue") if isinstance(source, dict) else None
            if not isinstance(issue, dict):
                continue
            if "pull_request" in issue and issue.get("state") == "open":
                return True
        return False
    except Exception:
        logger.warning("timeline fetch failed for %s/%s#%s", owner, name, number)
        return False


def _enrich_issues(owner: str, name: str, repo: str, items: list[dict]) -> list[Issue]:
    if not items:
        return []
    issues = [_issue_from_json(item, repo) for item in items]
    with ThreadPoolExecutor(max_workers=_ENRICH_WORKERS) as pool:
        comment_futs = [pool.submit(_fetch_comments, owner, name, issue.number) for issue in issues]
        pr_futs = [pool.submit(_linked_pr_open, owner, name, issue.number) for issue in issues]
        comments = [fut.result() for fut in comment_futs]
        linked = [fut.result() for fut in pr_futs]
    return [
        issue.model_copy(update={"comments": comments[i], "linked_pr_open": linked[i]})
        for i, issue in enumerate(issues)
    ]


def fetch_issues(repo: str, tags: list[str] | None = None, limit: int = 30) -> list[Issue]:
    owner, name = _split_repo(repo)
    effective = tags or list(DEFAULT_TAGS)
    raw: list[dict] = []
    for page in (1, 2):
        resp = _get(
            f"/repos/{owner}/{name}/issues",
            params={"state": "open", "per_page": 100, "page": page},
        )
        _raise_for_github(resp)
        batch = resp.json()
        if not isinstance(batch, list):
            raise UpstreamError("GitHub returned a non-list issues payload")
        raw.extend(batch)
        if len(batch) < 100:
            break

    kept: list[dict] = []
    for item in raw:
        if not isinstance(item, dict) or "pull_request" in item:
            continue
        if not labels_match(_label_names(item), effective):
            continue
        kept.append(item)
        if len(kept) >= limit:
            break
    return _enrich_issues(owner, name, repo, kept)


def fetch_new_issues(repo: str, etag: str | None) -> tuple[list[Issue], str | None]:
    owner, name = _split_repo(repo)
    extra: dict[str, str] = {}
    if etag is not None:
        extra["If-None-Match"] = etag
    resp = _get(
        f"/repos/{owner}/{name}/issues",
        params={"state": "open", "sort": "created", "direction": "desc", "per_page": 30},
        extra_headers=extra or None,
    )
    if resp.status_code == 304:
        return [], etag
    _raise_for_github(resp)
    batch = resp.json()
    if not isinstance(batch, list):
        raise UpstreamError("GitHub returned a non-list issues payload")
    issues: list[Issue] = []
    for item in batch:
        if not isinstance(item, dict) or "pull_request" in item:
            continue
        # Watcher only needs id/labels/status signals on the issue itself
        # (assignees, updated_at, body, labels). Skip per-issue comment/timeline
        # fetches here so polling stays cheap.
        issues.append(_issue_from_json(item, repo, comments=[], linked_pr_open=False))
    return issues, resp.headers.get("ETag") or etag


def fetch_readme(repo: str) -> str:
    owner, name = _split_repo(repo)
    resp = _get(
        f"/repos/{owner}/{name}/readme",
        accept="application/vnd.github.raw+json",
    )
    if resp.status_code == 404:
        return ""
    _raise_for_github(resp)
    return resp.text or ""
