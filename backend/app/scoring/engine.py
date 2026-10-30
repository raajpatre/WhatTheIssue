from app.schemas import Issue, ScoredIssue

_STATUS_ORDER = {"safe": 0, "unclear": 1, "stale": 2, "claimed": 3}


def score_issue(issue: Issue) -> ScoredIssue:
    return ScoredIssue(
        issue=issue,
        score=50,
        status="unclear",
        reasons=["Not scored yet"],
    )


def rank(issues: list[Issue]) -> list[ScoredIssue]:
    scored = [score_issue(issue) for issue in issues]
    scored.sort(key=lambda item: (_STATUS_ORDER.get(item.status, 99), -item.score))
    return scored
