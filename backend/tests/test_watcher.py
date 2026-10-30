"""
backend/tests/test_watcher.py — Part C Unit Tests

Covers:
- First run baseline (marks issues seen, stores etag, sends NO notification)
- check_all_now: new matching issue notifies once
- check_all_now: claimed issue skipped
- check_all_now: non-matching label skipped
- check_all_now: one repo failing does not stop others
- format_alert: escaping and layout
- notify.send: Telegram delivery & fallback
- telegram_bot: /start, /track, /list, /untrack command handling
- demo_create_issue: DEMO_REPO refusal enforcement
"""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure project root and backend are on sys.path
test_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(test_dir, ".."))
project_root = os.path.abspath(os.path.join(backend_path, ".."))

for p in (project_root, backend_path):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.notify import format_alert, send
from app.notify.telegram import send_telegram_message
from app.notify.telegram_bot import handle_message, parse_track_command
from app.watcher import service as watcher_service
from scripts.demo_create_issue import create_demo_issue


# ---------------------------------------------------------
# Mock Data Fixtures
# ---------------------------------------------------------

class DummyIssue:
    def __init__(self, id, repo, number, title, labels=None, url=None):
        self.id = id
        self.repo = repo
        self.number = number
        self.title = title
        self.labels = labels or []
        self.url = url or f"https://github.com/{repo}/issues/{number}"


class DummyScoredIssue:
    def __init__(self, issue, score=85, status="safe", reasons=None):
        self.issue = issue
        self.score = score
        self.status = status
        self.reasons = reasons or ["Clear reproduction steps", "No active assignees"]


class DummyWatch:
    def __init__(self, id, repo, tags=None, channel="telegram", contact="123456"):
        self.id = id
        self.repo = repo
        self.tags = tags or ["good first issue"]
        self.channel = channel
        self.contact = contact


# ---------------------------------------------------------
# C2: Alert Formatting & Notification Tests
# ---------------------------------------------------------

def test_format_alert_content_and_escaping():
    issue = DummyIssue(
        id=101,
        repo="my-org/my-project",
        number=1,
        title="Fix <script>alert('xss')</script> in docs & tutorials",
    )
    scored = DummyScoredIssue(
        issue=issue,
        score=90,
        status="safe",
        reasons=["Clean issue body", "Tag <beginner> friendly"],
    )

    alert = format_alert(scored)

    # Must contain repo, status, score
    assert "my-org/my-project" in alert
    assert "SAFE" in alert
    assert "90/100" in alert
    # Untrusted characters MUST be escaped
    assert "<script>" not in alert
    assert "&lt;script&gt;" in alert
    assert "&amp;" in alert
    assert "https://github.com/my-org/my-project/issues/1" in alert


def test_notify_send_telegram_success():
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ok = send_telegram_message("99999", "Hello test", token="test_token_123")
        assert ok is True
        mock_post.assert_called_once()


def test_notify_send_telegram_failure_does_not_raise():
    with patch("httpx.Client.post", side_effect=Exception("Connection reset")):
        # Must return False, never raise
        ok = send_telegram_message("99999", "Hello test", token="test_token_123")
        assert ok is False


def test_notify_send_channel_dispatch():
    with patch("app.notify.send_telegram_message", return_value=True) as mock_tg:
        assert send("telegram", "12345", "test") is True
        mock_tg.assert_called_once_with(chat_id="12345", text="test")

    # Unsupported channels should safely return False
    assert send("email", "user@example.com", "test") is False
    assert send("sms", "+123456789", "test") is False


# ---------------------------------------------------------
# C1: Baseline Repo Tests
# ---------------------------------------------------------

def test_baseline_repo_marks_seen_and_sends_no_notifications():
    mock_client = MagicMock()
    mock_crud = MagicMock()
    mock_notify = MagicMock()

    issue1 = DummyIssue(1, "org/repo", 1, "First")
    issue2 = DummyIssue(2, "org/repo", 2, "Second")
    mock_client.fetch_new_issues.return_value = ([issue1, issue2], "etag-1234")

    with patch.object(watcher_service, "github_client", mock_client), \
         patch.object(watcher_service, "crud", mock_crud), \
         patch.object(watcher_service, "notify_send", mock_notify):

        watcher_service.baseline_repo("org/repo")

        # Must fetch with etag=None
        mock_client.fetch_new_issues.assert_called_once_with("org/repo", etag=None)
        # Must save new etag and seen issue IDs
        mock_crud.set_etag.assert_called_once_with("org/repo", "etag-1234")
        mock_crud.add_seen_issue_ids.assert_called_once_with("org/repo", [1, 2])
        # Must NOT notify anyone
        mock_notify.assert_not_called()


# ---------------------------------------------------------
# C1: Check All Now Tests
# ---------------------------------------------------------

def test_check_all_now_new_matching_issue_notifies_once():
    mock_client = MagicMock()
    mock_crud = MagicMock()
    mock_scoring = MagicMock()

    mock_crud.distinct_watched_repos.return_value = ["org/repo"]
    mock_crud.get_etag.return_value = "etag-old"
    mock_crud.get_seen_issue_ids.return_value = {1}  # issue 1 is already seen

    new_issue = DummyIssue(2, "org/repo", 2, "New starter issue", labels=["good first issue"])
    mock_client.fetch_new_issues.return_value = ([new_issue], "etag-new")

    scored = DummyScoredIssue(new_issue, score=90, status="safe")
    mock_scoring.score_issue.return_value = scored

    watch = DummyWatch(id=1, repo="org/repo", tags=["good first issue"], channel="telegram", contact="999")
    mock_crud.list_watches.return_value = [watch]

    with patch.object(watcher_service, "github_client", mock_client), \
         patch.object(watcher_service, "crud", mock_crud), \
         patch.object(watcher_service, "scoring_engine", mock_scoring), \
         patch.object(watcher_service, "notify_send", return_value=True) as mock_send:

        result = watcher_service.check_all_now()

        assert result == {"checked": 1, "notified": 1}
        mock_send.assert_called_once()
        # Must mark the fresh issue as seen
        mock_crud.add_seen_issue_ids.assert_called_once_with("org/repo", [2])
        mock_crud.set_etag.assert_called_once_with("org/repo", "etag-new")


def test_check_all_now_claimed_issue_skipped():
    mock_client = MagicMock()
    mock_crud = MagicMock()
    mock_scoring = MagicMock()

    mock_crud.distinct_watched_repos.return_value = ["org/repo"]
    mock_crud.get_etag.return_value = None
    mock_crud.get_seen_issue_ids.return_value = set()

    claimed_issue = DummyIssue(10, "org/repo", 10, "Taken issue", labels=["good first issue"])
    mock_client.fetch_new_issues.return_value = ([claimed_issue], "etag-10")

    # Status is "claimed" -> should NOT notify
    scored = DummyScoredIssue(claimed_issue, score=30, status="claimed")
    mock_scoring.score_issue.return_value = scored

    watch = DummyWatch(id=1, repo="org/repo", tags=["good first issue"])
    mock_crud.list_watches.return_value = [watch]

    with patch.object(watcher_service, "github_client", mock_client), \
         patch.object(watcher_service, "crud", mock_crud), \
         patch.object(watcher_service, "scoring_engine", mock_scoring), \
         patch.object(watcher_service, "notify_send") as mock_send:

        result = watcher_service.check_all_now()

        assert result == {"checked": 1, "notified": 0}
        mock_send.assert_not_called()
        # Still marks as seen so we don't re-evaluate
        mock_crud.add_seen_issue_ids.assert_called_once_with("org/repo", [10])


def test_check_all_now_non_matching_label_skipped():
    mock_client = MagicMock()
    mock_crud = MagicMock()
    mock_scoring = MagicMock()

    mock_crud.distinct_watched_repos.return_value = ["org/repo"]
    mock_crud.get_etag.return_value = None
    mock_crud.get_seen_issue_ids.return_value = set()

    issue = DummyIssue(20, "org/repo", 20, "Refactor core", labels=["enhancement", "needs-triage"])
    mock_client.fetch_new_issues.return_value = ([issue], "etag-20")

    scored = DummyScoredIssue(issue, score=80, status="safe")
    mock_scoring.score_issue.return_value = scored

    # Watch is only for "good first issue"
    watch = DummyWatch(id=1, repo="org/repo", tags=["good first issue"])
    mock_crud.list_watches.return_value = [watch]

    with patch.object(watcher_service, "github_client", mock_client), \
         patch.object(watcher_service, "crud", mock_crud), \
         patch.object(watcher_service, "scoring_engine", mock_scoring), \
         patch.object(watcher_service, "notify_send") as mock_send:

        result = watcher_service.check_all_now()

        assert result == {"checked": 1, "notified": 0}
        mock_send.assert_not_called()
        mock_crud.add_seen_issue_ids.assert_called_once_with("org/repo", [20])


def test_check_all_now_one_repo_failing_does_not_stop_others():
    mock_client = MagicMock()
    mock_crud = MagicMock()
    mock_scoring = MagicMock()

    mock_crud.distinct_watched_repos.return_value = ["failing/repo", "working/repo"]
    mock_crud.get_etag.return_value = None
    mock_crud.get_seen_issue_ids.return_value = set()

    good_issue = DummyIssue(55, "working/repo", 1, "Good issue", labels=["good first issue"])

    def mock_fetch(repo, etag):
        if repo == "failing/repo":
            raise RuntimeError("Upstream GitHub 502")
        return ([good_issue], "etag-working")

    mock_client.fetch_new_issues.side_effect = mock_fetch

    scored = DummyScoredIssue(good_issue, status="safe")
    mock_scoring.score_issue.return_value = scored

    watch = DummyWatch(id=2, repo="working/repo", tags=["good first issue"])
    mock_crud.list_watches.return_value = [watch]

    with patch.object(watcher_service, "github_client", mock_client), \
         patch.object(watcher_service, "crud", mock_crud), \
         patch.object(watcher_service, "scoring_engine", mock_scoring), \
         patch.object(watcher_service, "notify_send", return_value=True) as mock_send:

        result = watcher_service.check_all_now()

        # Both repos checked, working one notified
        assert result == {"checked": 2, "notified": 1}
        mock_send.assert_called_once()


# ---------------------------------------------------------
# C2: Telegram Bot Command Parsing & Handling Tests
# ---------------------------------------------------------

def test_parse_track_command():
    repo, tags = parse_track_command("facebook/react")
    assert repo == "facebook/react"
    assert tags == ["good first issue"]

    repo2, tags2 = parse_track_command("https://github.com/torvalds/linux.git [kernel, novice]")
    assert repo2 == "torvalds/linux"
    assert tags2 == ["kernel", "novice"]

    with pytest.raises(ValueError):
        parse_track_command("invalid_repo_without_slash")


def test_telegram_bot_command_flow():
    mock_crud = MagicMock()
    mock_send = MagicMock()

    with patch("app.notify.telegram_bot.crud", mock_crud), \
         patch("app.notify.telegram_bot.send_telegram_message", mock_send):

        # 1. /start
        handle_message("123", "/start")
        mock_send.assert_called()
        assert "123" in mock_send.call_args[0][1]

        # 2. /list with empty watches
        mock_crud.list_watches.return_value = []
        handle_message("123", "/list")
        assert "no active watches" in mock_send.call_args[0][1]

        # 3. /untrack
        mock_crud.delete_watch.return_value = True
        handle_message("123", "/untrack 42")
        mock_crud.delete_watch.assert_called_with(42)
        assert "removed watch" in mock_send.call_args[0][1]


# ---------------------------------------------------------
# C3: Demo Create Issue Security Enforcement
# ---------------------------------------------------------

def test_demo_create_issue_refuses_non_demo_repo(monkeypatch):
    monkeypatch.setenv("DEMO_REPO", "myorg/my-demo-repo")
    monkeypatch.setenv("DEMO_GITHUB_TOKEN", "mock_token")

    # Should raise PermissionError when targeting any repo except DEMO_REPO
    with pytest.raises(PermissionError) as exc_info:
        create_demo_issue(target_repo="other-org/other-repo")

    assert "REFUSAL: Target repo 'other-org/other-repo' is not DEMO_REPO" in str(exc_info.value)


# ---------------------------------------------------------
# C1: Scheduler Lifecycle & Double-start Guard
# ---------------------------------------------------------

def test_start_scheduler_gated_by_env(monkeypatch):
    watcher_service.stop_scheduler()

    # When ENABLE_SCHEDULER=0, APScheduler should not start
    monkeypatch.setenv("ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_TELEGRAM_BOT", "0")

    with patch("app.watcher.service.BackgroundScheduler") as mock_sched:
        watcher_service.start_scheduler()
        mock_sched.assert_not_called()

        # Second call should be a no-op due to double-start guard
        watcher_service.start_scheduler()
        mock_sched.assert_not_called()

    watcher_service.stop_scheduler()


def test_start_scheduler_when_enabled(monkeypatch):
    watcher_service.stop_scheduler()

    monkeypatch.setenv("ENABLE_SCHEDULER", "1")
    monkeypatch.setenv("ENABLE_TELEGRAM_BOT", "0")
    monkeypatch.setenv("POLL_INTERVAL_MINUTES", "5")

    with patch("app.watcher.service.BackgroundScheduler") as mock_sched_cls:
        mock_instance = MagicMock()
        mock_sched_cls.return_value = mock_instance

        watcher_service.start_scheduler()
        mock_instance.add_job.assert_called_once()
        mock_instance.start.assert_called_once()

    watcher_service.stop_scheduler()

