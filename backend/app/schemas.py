# NEEDS-FROM-PART-A: backend/app/schemas.py is owned by Part A (copy from AGENTS.md verbatim).
# Providing here per AGENTS.md contract so Part B can run independently without waiting.

from typing import Literal, Optional
from pydantic import BaseModel

class Comment(BaseModel):
    author: str
    body: str
    created_at: str            # ISO 8601
    author_association: str    # "OWNER" | "MEMBER" | "COLLABORATOR" | "CONTRIBUTOR" | "NONE" ...

class Issue(BaseModel):
    id: int                    # GitHub global issue id
    repo: str                  # "owner/name"
    number: int
    title: str
    body: str = ""
    url: str                   # html_url
    labels: list[str] = []
    assignees: list[str] = []
    comments_count: int = 0
    comments: list[Comment] = []      # latest <= 10
    linked_pr_open: bool = False      # an open PR references this issue
    created_at: str
    updated_at: str

class AIInsight(BaseModel):
    summary: str                      # plain English, <= 3 sentences
    files_to_touch: list[str] = []
    skills_needed: list[str] = []
    first_steps: list[str] = []       # <= 5
    beginner_rating: int              # 0-10, 10 = easiest
    provider: str = ""                # "gemini" | "ollama" | "fallback"

class ScoredIssue(BaseModel):
    issue: Issue
    score: int                        # 0-100
    status: Literal["safe", "claimed", "stale", "unclear"]
    reasons: list[str] = []           # human-readable, shown in the UI
    ai: Optional[AIInsight] = None

class ReadmeSuggestion(BaseModel):
    title: str
    description: str
    area: str                         # "docs" | "tests" | "bugfix" | "feature" | "setup" | "other"
    why_beginner_friendly: str

class WatchIn(BaseModel):
    repo: str                         # "owner/name"
    tags: list[str] = ["good first issue"]
    channel: Literal["telegram", "email"] = "telegram"
    contact: str                      # telegram chat_id (as string) or email

class Watch(WatchIn):
    id: int
    created_at: str
