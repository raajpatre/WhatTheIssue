import json
import re
from pathlib import Path
from urllib.parse import urlparse

from app.github.labels import labels_match
from app.schemas import Issue

DEFAULT_TAGS = ["good first issue"]
_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


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


def _fixture_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        Path("fixtures/sample_issues.json"),
        Path("../fixtures/sample_issues.json"),
        here.parents[3] / "fixtures" / "sample_issues.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("fixtures/sample_issues.json not found")


def _load_fixture_issues(repo: str) -> list[Issue]:
    data = json.loads(_fixture_path().read_text())
    issues: list[Issue] = []
    for item in data:
        issue = Issue.model_validate(item)
        issues.append(issue.model_copy(update={"repo": repo}))
    return issues


def fetch_issues(repo: str, tags: list[str] | None = None, limit: int = 30) -> list[Issue]:
    effective = tags if tags else list(DEFAULT_TAGS)
    matched = [issue for issue in _load_fixture_issues(repo) if labels_match(issue.labels, effective)]
    return matched[:limit]


def fetch_new_issues(repo: str, etag: str | None) -> tuple[list[Issue], str | None]:
    return _load_fixture_issues(repo)[:30], None


def fetch_readme(repo: str) -> str:
    return f"# {repo}\n\nPlaceholder README for the skeleton.\n"
