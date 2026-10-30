from fastapi import APIRouter

from app.ai import service as ai
from app.api.errors import RepoNotFoundError
from app.db import crud
from app.github.client import DEFAULT_TAGS, fetch_issues, parse_repo
from app.schemas import AIInsight

router = APIRouter()


@router.get("/issues/{owner}/{name}/{number}/explain")
def explain_issue(owner: str, name: str, number: int) -> AIInsight:
    repo = parse_repo(f"{owner}/{name}")
    cached = crud.get_ai_insight(repo, number)
    if cached is not None:
        return cached
    issue = crud.get_issue(repo, number)
    if issue is None:
        fetched = fetch_issues(repo, tags=DEFAULT_TAGS)
        crud.upsert_issues(repo, fetched)
        issue = crud.get_issue(repo, number)
    if issue is None:
        # CONTRACT-QUESTION: no contract code for a missing issue number; using REPO_NOT_FOUND.
        raise RepoNotFoundError(f"Issue {repo}#{number} not found")
    insight = ai.explain_issue(issue)
    crud.save_ai_insight(repo, number, insight)
    return insight
