from app.schemas import ScoredIssue


def send(channel: str, contact: str, text: str) -> bool:
    return True


def format_alert(s: ScoredIssue) -> str:
    return f"New issue in {s.issue.repo}: {s.issue.title}"
