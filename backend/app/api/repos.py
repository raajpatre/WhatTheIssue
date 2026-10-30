import time

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.ai import service as ai
from app.db import crud
from app.github.client import DEFAULT_TAGS, fetch_issues, fetch_readme, parse_repo
from app.schemas import ReadmeSuggestion, ScoredIssue
from app.scoring.engine import rank

router = APIRouter()
_ISSUE_TTL = 300
_SUGGEST_TTL = 3600
_issue_cache: dict[tuple[str, tuple[str, ...]], tuple[float, list[ScoredIssue]]] = {}
_suggest_cache: dict[str, tuple[float, list[ReadmeSuggestion]]] = {}

EMPTY_NOTE = "No issues matched these labels. Try the README suggestions."


class RepoIn(BaseModel):
    url: str
    tags: list[str] | None = None


def _parse_tags(tags: str | None) -> list[str]:
    if not tags or not tags.strip():
        return list(DEFAULT_TAGS)
    parts = [part.strip() for part in tags.split(",")]
    return [part for part in parts if part] or list(DEFAULT_TAGS)


async def _scored_issues(repo: str, tags: list[str]) -> list[ScoredIssue]:
    key = (repo, tuple(tags))
    hit = _issue_cache.get(key)
    now = time.time()
    if hit and now - hit[0] < _ISSUE_TTL:
        scored = hit[1]
    else:
        issues = await run_in_threadpool(fetch_issues, repo, tags)
        scored = rank(issues)
        crud.upsert_issues(repo, issues)
        _issue_cache[key] = (now, scored)
    attached: list[ScoredIssue] = []
    for item in scored:
        insight = crud.get_ai_insight(repo, item.issue.number)
        attached.append(item.model_copy(update={"ai": insight}) if insight else item)
    return attached


@router.post("/repos")
async def add_repo(body: RepoIn) -> dict:
    repo = parse_repo(body.url)
    tags = body.tags or list(DEFAULT_TAGS)
    issues = await run_in_threadpool(fetch_issues, repo, tags)
    scored = rank(issues)
    crud.upsert_issues(repo, issues)
    note = None if scored else EMPTY_NOTE
    return {"repo": repo, "issues": scored, "note": note}


@router.get("/repos/{owner}/{name}/issues")
async def list_issues(
    owner: str,
    name: str,
    tags: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[ScoredIssue]:
    repo = parse_repo(f"{owner}/{name}")
    parsed_tags = _parse_tags(tags)
    scored = await _scored_issues(repo, parsed_tags)
    if status:
        scored = [item for item in scored if item.status == status]
    return scored


@router.get("/repos/{owner}/{name}/suggestions")
async def list_suggestions(owner: str, name: str) -> list[ReadmeSuggestion]:
    repo = parse_repo(f"{owner}/{name}")
    hit = _suggest_cache.get(repo)
    now = time.time()
    if hit and now - hit[0] < _SUGGEST_TTL:
        return hit[1]
    readme = await run_in_threadpool(fetch_readme, repo)
    suggestions = await run_in_threadpool(ai.suggest_from_readme, repo, readme)
    _suggest_cache[repo] = (now, suggestions)
    return suggestions
