import threading
from datetime import datetime, timezone

from app.schemas import AIInsight, Issue, Watch, WatchIn

_lock = threading.Lock()
_issues: dict[tuple[str, int], Issue] = {}
_seen: dict[str, set[int]] = {}
_etags: dict[str, str | None] = {}
_watches: dict[int, Watch] = {}
_next_watch_id = 1
_insights: dict[tuple[str, int], AIInsight] = {}


def upsert_issues(repo: str, issues: list[Issue]) -> None:
    with _lock:
        for issue in issues:
            stored = issue.model_copy(update={"repo": repo})
            _issues[(repo, stored.number)] = stored


def get_issue(repo: str, number: int) -> Issue | None:
    with _lock:
        return _issues.get((repo, number))


def get_seen_issue_ids(repo: str) -> set[int]:
    with _lock:
        return set(_seen.get(repo, set()))


def add_seen_issue_ids(repo: str, ids: list[int]) -> None:
    with _lock:
        _seen.setdefault(repo, set()).update(ids)


def get_etag(repo: str) -> str | None:
    with _lock:
        return _etags.get(repo)


def set_etag(repo: str, etag: str | None) -> None:
    with _lock:
        _etags[repo] = etag


def create_watch(w: WatchIn) -> Watch:
    global _next_watch_id
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with _lock:
        watch_id = _next_watch_id
        _next_watch_id += 1
        watch = Watch(
            repo=w.repo,
            tags=list(w.tags),
            channel=w.channel,
            contact=w.contact,
            id=watch_id,
            created_at=created_at,
        )
        _watches[watch_id] = watch
        return watch


def list_watches(contact: str | None = None, repo: str | None = None) -> list[Watch]:
    with _lock:
        watches = list(_watches.values())
    if contact is not None:
        watches = [w for w in watches if w.contact == contact]
    if repo is not None:
        watches = [w for w in watches if w.repo == repo]
    return watches


def delete_watch(watch_id: int) -> bool:
    with _lock:
        return _watches.pop(watch_id, None) is not None


def distinct_watched_repos() -> list[str]:
    with _lock:
        return sorted({w.repo for w in _watches.values()})


def get_ai_insight(repo: str, number: int) -> AIInsight | None:
    with _lock:
        return _insights.get((repo, number))


def save_ai_insight(repo: str, number: int, insight: AIInsight) -> None:
    with _lock:
        _insights[(repo, number)] = insight
