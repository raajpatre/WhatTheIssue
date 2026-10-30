"""
Part B - AI Service Layer
Provides explain_issue and suggest_from_readme.
NEVER raises exceptions; falls back cleanly.
"""

from collections import OrderedDict
import json
import logging
import os
import re
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.schemas import Issue, AIInsight, ReadmeSuggestion
from app.scoring.engine import score_issue
from app.ai.prompts import build_explain_prompt, build_readme_prompt
from app.ai.providers import get_provider
from app.ai.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# LRU Cache for explanations (capacity 100)
_EXPLAIN_CACHE: "OrderedDict[tuple[str, int, str], AIInsight]" = OrderedDict()
_CACHE_MAX_SIZE = 100

RE_FILE_PATH = re.compile(
    r'\b(?:[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,10})\b|\b(?:[a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-\.]+)\b'
)


class _RawAIInsight(BaseModel):
    summary: str
    files_to_touch: list[str] = []
    skills_needed: list[str] = []
    first_steps: list[str] = []
    beginner_rating: int


class _RawReadmeSuggestions(BaseModel):
    suggestions: list[ReadmeSuggestion] = []


def _extract_json_substring(text: str) -> Optional[dict]:
    """Helper to extract JSON object from LLM response text."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try matching first { ... }
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _fallback_explain(issue: Issue) -> AIInsight:
    """Deterministic fallback when LLM fails or is unavailable."""
    body_stripped = (issue.body or "").strip()
    summary = body_stripped[:200] if body_stripped else f"Issue #{issue.number}: {issue.title}"
    if len(body_stripped) > 200:
        summary += "..."

    # Extract file paths mentioned in title + body
    text_to_search = f"{issue.title}\n{issue.body or ''}"
    matches = RE_FILE_PATH.findall(text_to_search)
    # Deduplicate matches
    files_to_touch = []
    seen = set()
    for m in matches:
        if m not in seen and not m.startswith("http"):
            seen.add(m)
            files_to_touch.append(m)

    scored = score_issue(issue)
    beginner_rating = max(0, min(10, round(scored.score / 10)))

    skills = []
    for lbl in issue.labels:
        if lbl.lower() not in ("good first issue", "good-first-issue", "help wanted"):
            skills.append(lbl)

    first_steps = [
        "1. Fork and clone the repository locally",
        "2. Review the issue description and mentioned files",
        "3. Run existing tests to verify setup",
    ]

    return AIInsight(
        summary=summary,
        files_to_touch=files_to_touch,
        skills_needed=skills,
        first_steps=first_steps,
        beginner_rating=beginner_rating,
        provider="fallback",
    )


def explain_issue(
    issue: Issue,
    provider: Optional[LLMProvider] = None,
) -> AIInsight:
    """
    Explain an issue in plain English.
    Audience: newcomer to open source.
    Never raises an exception; falls back to deterministic heuristic insight.
    Uses in-memory LRU cache keyed by (repo, number, updated_at).
    """
    cache_key = (issue.repo, issue.number, issue.updated_at)
    if cache_key in _EXPLAIN_CACHE:
        # Move to end for LRU
        _EXPLAIN_CACHE.move_to_end(cache_key)
        return _EXPLAIN_CACHE[cache_key]

    active_provider = provider or get_provider()
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower().strip()

    prompt = build_explain_prompt(issue)

    # Try generate, with 1 retry on invalid JSON
    insight = None
    for attempt in range(2):
        try:
            raw_response = active_provider.generate(prompt)
            data = _extract_json_substring(raw_response)
            if data is not None:
                parsed = _RawAIInsight(**data)
                # Ensure beginner rating is clamped 0-10
                rating = max(0, min(10, parsed.beginner_rating))
                # Validate files_to_touch: only keep paths present in issue text
                full_text = f"{issue.title}\n{issue.body or ''}"
                valid_files = [f for f in parsed.files_to_touch if f in full_text]

                insight = AIInsight(
                    summary=parsed.summary,
                    files_to_touch=valid_files,
                    skills_needed=parsed.skills_needed,
                    first_steps=parsed.first_steps[:5],
                    beginner_rating=rating,
                    provider=provider_name,
                )
                break
        except Exception as e:
            logger.warning(f"explain_issue LLM attempt {attempt+1} failed: {e}")

    if insight is None:
        insight = _fallback_explain(issue)

    # Update LRU cache
    _EXPLAIN_CACHE[cache_key] = insight
    if len(_EXPLAIN_CACHE) > _CACHE_MAX_SIZE:
        _EXPLAIN_CACHE.popitem(last=False)

    return insight


def suggest_from_readme(
    repo: str,
    readme: str,
    provider: Optional[LLMProvider] = None,
) -> list[ReadmeSuggestion]:
    """
    Suggest 3-5 starter contribution ideas from the README.
    If the README is empty, returns [].
    Never raises an exception.
    """
    if not readme or not readme.strip():
        return []

    active_provider = provider or get_provider()
    prompt = build_readme_prompt(repo, readme)

    for attempt in range(2):
        try:
            raw_response = active_provider.generate(prompt)
            data = _extract_json_substring(raw_response)
            if data is not None:
                # Could be {"suggestions": [...]} or list directly
                if isinstance(data, list):
                    items = data
                else:
                    items = data.get("suggestions", [])
                
                valid_areas = {"docs", "tests", "bugfix", "feature", "setup", "other"}
                result = []
                for item in items:
                    area = item.get("area", "other")
                    if area not in valid_areas:
                        area = "other"
                    item["area"] = area
                    result.append(ReadmeSuggestion(**item))
                if result:
                    return result
        except Exception as e:
            logger.warning(f"suggest_from_readme attempt {attempt+1} failed: {e}")

    return []
