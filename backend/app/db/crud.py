import json
from contextlib import contextmanager
from datetime import datetime, timezone

from app.db.models import AIInsightRow, IssueRow, RepoRow, SeenIssueRow, WatchRow
from app.db.session import get_session
from app.schemas import AIInsight, Issue, Watch, WatchIn


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _session():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_issues(repo: str, issues: list[Issue]) -> None:
    with _session() as session:
        for issue in issues:
            stored = issue.model_copy(update={"repo": repo})
            payload = json.dumps(stored.model_dump())
            row = session.get(IssueRow, stored.id)
            if row is None:
                session.add(
                    IssueRow(
                        id=stored.id,
                        repo=repo,
                        number=stored.number,
                        payload=payload,
                        updated_at=stored.updated_at,
                    )
                )
            else:
                row.repo = repo
                row.number = stored.number
                row.payload = payload
                row.updated_at = stored.updated_at


def get_issue(repo: str, number: int) -> Issue | None:
    with _session() as session:
        row = (
            session.query(IssueRow)
            .filter(IssueRow.repo == repo, IssueRow.number == number)
            .one_or_none()
        )
        if row is None:
            return None
        return Issue.model_validate(json.loads(row.payload))


def get_seen_issue_ids(repo: str) -> set[int]:
    with _session() as session:
        rows = session.query(SeenIssueRow).filter(SeenIssueRow.repo == repo).all()
        return {row.issue_id for row in rows}


def add_seen_issue_ids(repo: str, ids: list[int]) -> None:
    unique_ids = set(ids)
    with _session() as session:
        existing = {
            row.issue_id
            for row in session.query(SeenIssueRow).filter(SeenIssueRow.repo == repo).all()
        }
        for issue_id in unique_ids - existing:
            session.add(SeenIssueRow(repo=repo, issue_id=issue_id))


def get_etag(repo: str) -> str | None:
    with _session() as session:
        row = session.get(RepoRow, repo)
        return None if row is None else row.etag


def set_etag(repo: str, etag: str | None) -> None:
    with _session() as session:
        row = session.get(RepoRow, repo)
        fetched_at = _now_iso()
        if row is None:
            session.add(RepoRow(full_name=repo, etag=etag, last_fetched_at=fetched_at))
        else:
            row.etag = etag
            row.last_fetched_at = fetched_at


def create_watch(w: WatchIn) -> Watch:
    created_at = _now_iso()
    with _session() as session:
        row = WatchRow(
            repo=w.repo,
            tags_json=json.dumps(list(w.tags)),
            channel=w.channel,
            contact=w.contact,
            created_at=created_at,
        )
        session.add(row)
        session.flush()
        return Watch(
            repo=row.repo,
            tags=list(w.tags),
            channel=row.channel,  # type: ignore[arg-type]
            contact=row.contact,
            id=int(row.id),
            created_at=row.created_at,
        )


def list_watches(contact: str | None = None, repo: str | None = None) -> list[Watch]:
    with _session() as session:
        query = session.query(WatchRow)
        if contact is not None:
            query = query.filter(WatchRow.contact == contact)
        if repo is not None:
            query = query.filter(WatchRow.repo == repo)
        rows = query.all()
        return [
            Watch(
                repo=row.repo,
                tags=json.loads(row.tags_json),
                channel=row.channel,  # type: ignore[arg-type]
                contact=row.contact,
                id=int(row.id),
                created_at=row.created_at,
            )
            for row in rows
        ]


def delete_watch(watch_id: int) -> bool:
    with _session() as session:
        row = session.get(WatchRow, watch_id)
        if row is None:
            return False
        session.delete(row)
        return True


def distinct_watched_repos() -> list[str]:
    with _session() as session:
        rows = session.query(WatchRow.repo).distinct().all()
        return sorted({row[0] for row in rows})


def get_ai_insight(repo: str, number: int) -> AIInsight | None:
    with _session() as session:
        row = session.get(AIInsightRow, (repo, number))
        if row is None:
            return None
        return AIInsight.model_validate(json.loads(row.payload))


def save_ai_insight(repo: str, number: int, insight: AIInsight) -> None:
    with _session() as session:
        payload = json.dumps(insight.model_dump())
        row = session.get(AIInsightRow, (repo, number))
        if row is None:
            session.add(
                AIInsightRow(
                    repo=repo,
                    number=number,
                    payload=payload,
                    created_at=_now_iso(),
                )
            )
        else:
            row.payload = payload
