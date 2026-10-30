import json
from datetime import datetime, timezone
from pathlib import Path
import pytest

from app.schemas import Issue, Comment
from app.scoring.engine import (
    score_issue,
    rank,
    get_current_time,
    determine_status,
)

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "sample_issues.json"


@pytest.fixture
def sample_issues():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Issue(**item) for item in data]


# Fixed reference time for deterministic testing: 2026-10-31 00:00:00 UTC
MOCK_NOW = datetime(2026, 10, 31, 0, 0, 0, tzinfo=timezone.utc)


def test_sample_issues_expected_statuses(sample_issues, monkeypatch):
    """
    Test sample_issues.json against expected statuses from PART-B-scoring-ai.md:
    id 101 -> safe
    id 102 -> claimed
    id 103 -> stale
    id 104 -> unclear
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    by_id = {issue.id: issue for issue in sample_issues}

    # Issue 101: Fix typo in installation docs
    scored_101 = score_issue(by_id[101])
    assert scored_101.status == "safe"
    assert scored_101.score >= 50
    assert len(scored_101.reasons) <= 6

    # Issue 102: Add unit tests for the date parser (assignee + claimed comment)
    scored_102 = score_issue(by_id[102])
    assert scored_102.status == "claimed"

    # Issue 103: Improve error message (last updated Jan 2025, > 180 days from Oct 2026)
    scored_103 = score_issue(by_id[103])
    assert scored_103.status == "stale"

    # Issue 104: fix it (body 'broken', < 40 chars)
    scored_104 = score_issue(by_id[104])
    assert scored_104.status == "unclear"


def test_maintainer_only_claim_phrase_not_claimed(monkeypatch):
    """
    Edge case: A maintainer (OWNER/MEMBER/COLLABORATOR) using a claim phrase
    must NOT count as claimed.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=201,
        repo="test/repo",
        number=1,
        title="Valid starter issue",
        body="This is a detailed issue description that is plenty long and has some steps to reproduce.",
        url="https://github.com/test/repo/issues/1",
        labels=["good first issue"],
        assignees=[],
        comments_count=1,
        comments=[
            Comment(
                author="lead-maintainer",
                body="I'll take a look at PRs for this when opened.",
                created_at="2026-10-30T10:00:00Z",
                author_association="OWNER",
            )
        ],
        linked_pr_open=False,
        created_at="2026-10-25T10:00:00Z",
        updated_at="2026-10-30T10:00:00Z",
    )
    scored = score_issue(issue)
    assert scored.status == "safe"


def test_contributor_claim_phrase_marks_claimed(monkeypatch):
    """
    A non-maintainer claiming within 14 days marks it claimed.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=202,
        repo="test/repo",
        number=2,
        title="Valid starter issue",
        body="This is a detailed issue description with enough length to be well-formed.",
        url="https://github.com/test/repo/issues/2",
        labels=["good first issue"],
        assignees=[],
        comments_count=1,
        comments=[
            Comment(
                author="random-dev",
                body="Can I work on this issue please?",
                created_at="2026-10-29T10:00:00Z",
                author_association="NONE",
            )
        ],
        linked_pr_open=False,
        created_at="2026-10-25T10:00:00Z",
        updated_at="2026-10-29T10:00:00Z",
    )
    scored = score_issue(issue)
    assert scored.status == "claimed"


def test_old_claim_phrase_past_14_days_does_not_claim(monkeypatch):
    """
    A claim phrase made 20 days ago should not keep the issue claimed if updated recently.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=203,
        repo="test/repo",
        number=3,
        title="Valid starter issue",
        body="This is a detailed issue description with enough length to be well-formed.",
        url="https://github.com/test/repo/issues/3",
        labels=["good first issue"],
        assignees=[],
        comments_count=1,
        comments=[
            Comment(
                author="ghost-dev",
                body="I will take this",
                created_at="2026-10-01T10:00:00Z",  # 30 days before MOCK_NOW
                author_association="NONE",
            )
        ],
        linked_pr_open=False,
        created_at="2026-09-25T10:00:00Z",
        updated_at="2026-10-20T10:00:00Z",  # Updated within 180 days
    )
    scored = score_issue(issue)
    assert scored.status == "safe"


def test_edge_case_empty_body(monkeypatch):
    """Empty body should result in 'unclear' status."""
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=204,
        repo="test/repo",
        number=4,
        title="Nothing here",
        body="",
        url="https://github.com/test/repo/issues/4",
        labels=["good first issue"],
        assignees=[],
        comments_count=0,
        comments=[],
        linked_pr_open=False,
        created_at="2026-10-25T10:00:00Z",
        updated_at="2026-10-25T10:00:00Z",
    )
    scored = score_issue(issue)
    assert scored.status == "unclear"
    assert scored.score <= 50


def test_edge_case_no_comments_missing_labels(monkeypatch):
    """Issue with no labels and no comments should be scored properly without crashes."""
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=205,
        repo="test/repo",
        number=5,
        title="Plain issue without metadata",
        body="This is a normal description that has just enough characters to pass the minimum body length check.",
        url="https://github.com/test/repo/issues/5",
        labels=[],
        assignees=[],
        comments_count=0,
        comments=[],
        linked_pr_open=False,
        created_at="2026-10-25T10:00:00Z",
        updated_at="2026-10-25T10:00:00Z",
    )
    scored = score_issue(issue)
    assert scored.status == "safe"
    assert 0 <= scored.score <= 100


def test_rank_ordering(sample_issues, monkeypatch):
    """
    Test rank: status order (safe, unclear, stale, claimed),
    then score descending.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    ranked = rank(sample_issues)
    statuses = [s.status for s in ranked]
    assert statuses == ["safe", "unclear", "stale", "claimed"]


def test_malformed_datetime_resilience(monkeypatch):
    """
    Security & edge-case: If GitHub API returns corrupted or non-ISO dates,
    the scoring engine must never crash or throw unhandled exceptions.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=206,
        repo="test/repo",
        number=6,
        title="Corrupted date strings",
        body="This is a test issue with corrupted date format strings.",
        url="https://github.com/test/repo/issues/6",
        labels=["good first issue"],
        assignees=[],
        comments_count=1,
        comments=[
            Comment(
                author="user",
                body="I'll take this!",
                created_at="NOT-A-DATE",
                author_association="NONE",
            )
        ],
        linked_pr_open=False,
        created_at="INVALID-CREATED-DATE",
        updated_at="MALFORMED-UPDATED-DATE",
    )
    scored = score_issue(issue)
    # The comment has claim phrase with unparseable date -> fallback assumes recent -> claimed
    assert scored.status == "claimed"
    assert 0 <= scored.score <= 100


def test_untrusted_html_and_script_tags_in_body(monkeypatch):
    """
    Rule 6: Untrusted input with embedded HTML and script tags
    must be treated strictly as raw text and scored safely.
    """
    monkeypatch.setattr("app.scoring.engine.get_current_time", lambda: MOCK_NOW)
    issue = Issue(
        id=207,
        repo="test/repo",
        number=7,
        title="<script>alert('xss')</script>",
        body="<img src=x onerror=alert(1)> Check file src/main.py for details on how to fix this bug.",
        url="https://github.com/test/repo/issues/7",
        labels=["good first issue"],
        assignees=[],
        comments_count=0,
        comments=[],
        linked_pr_open=False,
        created_at="2026-10-25T10:00:00Z",
        updated_at="2026-10-25T10:00:00Z",
    )
    scored = score_issue(issue)
    assert scored.status == "safe"
    assert any("file references" in r for r in scored.reasons)

