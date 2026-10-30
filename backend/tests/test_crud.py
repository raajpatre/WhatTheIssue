from app.db import crud
from app.db.session import init_db, reset_engine_for_tests
from app.schemas import AIInsight, Issue, WatchIn


def _issue(number: int, repo: str = "acme/widgets") -> Issue:
    return Issue(
        id=1000 + number,
        repo=repo,
        number=number,
        title=f"Issue {number}",
        body="hello",
        url=f"https://github.com/{repo}/issues/{number}",
        labels=["good first issue"],
        assignees=["alice"],
        comments_count=0,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-02T00:00:00Z",
    )


def test_upsert_and_get_issue(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'crud.db'}"
    monkeypatch.setattr("app.config.DATABASE_URL", url)
    reset_engine_for_tests(url)
    init_db()

    issue = _issue(7)
    crud.upsert_issues("acme/widgets", [issue])
    loaded = crud.get_issue("acme/widgets", 7)
    assert loaded is not None
    assert loaded.id == issue.id
    assert loaded.title == "Issue 7"
    assert loaded.repo == "acme/widgets"
    assert crud.get_issue("acme/widgets", 99) is None

    updated = issue.model_copy(update={"title": "Renamed"})
    crud.upsert_issues("acme/widgets", [updated])
    again = crud.get_issue("acme/widgets", 7)
    assert again is not None
    assert again.title == "Renamed"


def test_watches_crud(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'crud.db'}"
    monkeypatch.setattr("app.config.DATABASE_URL", url)
    reset_engine_for_tests(url)
    init_db()

    first = crud.create_watch(
        WatchIn(repo="acme/widgets", tags=["good first issue"], channel="telegram", contact="111")
    )
    assert first.id >= 1
    assert first.created_at.endswith("Z")
    second = crud.create_watch(
        WatchIn(repo="acme/other", tags=["help wanted"], channel="email", contact="a@b.c")
    )
    third = crud.create_watch(
        WatchIn(repo="acme/widgets", tags=["bug"], channel="telegram", contact="111")
    )

    all_watches = crud.list_watches()
    assert {w.id for w in all_watches} == {first.id, second.id, third.id}

    by_contact = crud.list_watches(contact="111")
    assert {w.id for w in by_contact} == {first.id, third.id}
    by_repo = crud.list_watches(repo="acme/other")
    assert [w.id for w in by_repo] == [second.id]
    both = crud.list_watches(contact="111", repo="acme/widgets")
    assert {w.id for w in both} == {first.id, third.id}

    assert crud.distinct_watched_repos() == ["acme/other", "acme/widgets"]
    assert crud.delete_watch(first.id) is True
    assert crud.delete_watch(first.id) is False
    assert {w.id for w in crud.list_watches()} == {second.id, third.id}


def test_seen_ids_etag_and_ai_insight(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'crud.db'}"
    monkeypatch.setattr("app.config.DATABASE_URL", url)
    reset_engine_for_tests(url)
    init_db()

    assert crud.get_seen_issue_ids("acme/widgets") == set()
    crud.add_seen_issue_ids("acme/widgets", [1, 2, 2])
    crud.add_seen_issue_ids("acme/widgets", [3])
    assert crud.get_seen_issue_ids("acme/widgets") == {1, 2, 3}
    assert crud.get_seen_issue_ids("other/repo") == set()

    assert crud.get_etag("acme/widgets") is None
    crud.set_etag("acme/widgets", 'W/"one"')
    assert crud.get_etag("acme/widgets") == 'W/"one"'
    crud.set_etag("acme/widgets", 'W/"two"')
    assert crud.get_etag("acme/widgets") == 'W/"two"'
    crud.set_etag("acme/widgets", None)
    assert crud.get_etag("acme/widgets") is None

    assert crud.get_ai_insight("acme/widgets", 7) is None
    insight = AIInsight(
        summary="Easy docs tweak.",
        files_to_touch=["README.md"],
        skills_needed=["markdown"],
        first_steps=["Open the README"],
        beginner_rating=9,
        provider="fallback",
    )
    crud.save_ai_insight("acme/widgets", 7, insight)
    loaded = crud.get_ai_insight("acme/widgets", 7)
    assert loaded == insight
    updated = insight.model_copy(update={"summary": "Even easier."})
    crud.save_ai_insight("acme/widgets", 7, updated)
    assert crud.get_ai_insight("acme/widgets", 7) == updated
