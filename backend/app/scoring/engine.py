"""
Part B - Scoring Engine
Pure functions: no network, no DB, no clock surprises.
"""

from datetime import datetime, timezone
import re
from typing import Callable, Optional

from app.schemas import Issue, ScoredIssue
from app.github.labels import labels_match

# ==========================================
# Tuning Constants & Weights (Part B contract)
# ==========================================
INITIAL_SCORE = 50
SCORE_MIN = 0
SCORE_MAX = 100

# Positive Signals
WEIGHT_GOOD_FIRST_ISSUE = 15
WEIGHT_HELP_WANTED = 5
WEIGHT_BODY_OPTIMAL_LENGTH = 10     # body 200–3000 chars
WEIGHT_HELPFUL_BODY_CONTENT = 10    # code block, file path, steps/expected
WEIGHT_MAINTAINER_COMMENTED = 10    # OWNER/MEMBER/COLLABORATOR commented
WEIGHT_RECENTLY_UPDATED = 5         # updated in the last 30 days

# Negative Signals
WEIGHT_EXCESSIVE_COMMENTS = -10     # comments_count > 15 (long debate)
WEIGHT_DIFFICULT_LABELS = -15       # hard, complex, epic, security, breaking, architecture
WEIGHT_BODY_OVERLY_LONG = -10       # body > 6000 chars
WEIGHT_STATUS_CLAIMED = -25
WEIGHT_STATUS_STALE = -30
WEIGHT_STATUS_UNCLEAR = -20

# Thresholds
DAYS_CLAIM_RECENCY = 14
DAYS_STALE = 180
DAYS_RECENT_ACTIVITY = 30
MIN_BODY_LEN = 40
OPTIMAL_BODY_MIN = 200
OPTIMAL_BODY_MAX = 3000
LONG_BODY_THRESHOLD = 6000
HIGH_COMMENTS_THRESHOLD = 15
MAX_REASONS = 6

# Canonical definitions
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

CLAIM_PHRASES = [
    "i'll take",
    "i will take",
    "i can take",
    "working on this",
    "working on it",
    "assign me",
    "assigned to me",
    "taking this",
    "i'd like to work",
    "i want to work",
    "can i work on",
    "on it",
]

DIFFICULT_LABEL_KEYWORDS = [
    "hard",
    "complex",
    "epic",
    "security",
    "breaking",
    "architecture",
]

GOOD_FIRST_ISSUE_TAGS = [
    "good first issue",
    "good-first-issue",
    "beginner",
    "starter",
    "easy",
]

HELP_WANTED_TAGS = [
    "help wanted",
    "help-wanted",
]

# Regex patterns
RE_FILE_PATH = re.compile(
    r'(?:[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,10})|(?:[a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-\.]+)'
)


def get_current_time() -> datetime:
    """Helper returning current UTC datetime. Monkeypatchable in tests."""
    return datetime.now(timezone.utc)


def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def determine_status(
    issue: Issue,
    now: datetime,
) -> tuple[str, list[str]]:
    """
    Status rules checked in order:
    1. claimed if: assignees is non-empty, OR linked_pr_open is true,
       OR a comment by someone whose author_association is not OWNER/MEMBER/COLLABORATOR,
       in the last 14 days, contains a claim phrase.
    2. stale if: last activity (updated_at) is more than 180 days old.
    3. unclear if: body is shorter than 40 characters after stripping.
    4. otherwise safe.
    """
    reasons = []

    # 1. Claimed check
    if issue.assignees:
        reasons.append(f"Assigned to {', '.join(issue.assignees)}")
        return "claimed", reasons

    if issue.linked_pr_open:
        reasons.append("An open pull request is already linked")
        return "claimed", reasons

    for comment in issue.comments:
        assoc = (comment.author_association or "").upper()
        if assoc not in MAINTAINER_ASSOCIATIONS:
            comment_dt = _parse_iso_datetime(comment.created_at)
            is_recent = False
            if comment_dt:
                age_days = (now - comment_dt).total_seconds() / 86400.0
                if age_days <= DAYS_CLAIM_RECENCY:
                    is_recent = True
            else:
                # If cannot parse timestamp, assume recent to be safe
                is_recent = True

            if is_recent:
                body_lower = comment.body.lower()
                for phrase in CLAIM_PHRASES:
                    if phrase in body_lower:
                        reasons.append(f"Someone recently commented: \"{phrase}\"")
                        return "claimed", reasons

    # 2. Stale check
    updated_dt = _parse_iso_datetime(issue.updated_at)
    if updated_dt:
        age_days = (now - updated_dt).total_seconds() / 86400.0
        if age_days > DAYS_STALE:
            reasons.append(f"Last activity was {int(age_days)} days ago")
            return "stale", reasons

    # 3. Unclear check
    body_stripped = (issue.body or "").strip()
    if len(body_stripped) < MIN_BODY_LEN:
        reasons.append("Issue description is very short or missing details")
        return "unclear", reasons

    # 4. Safe
    reasons.append("Issue is open and ready for contributors")
    return "safe", reasons


def score_issue(
    issue: Issue,
    now_fn: Optional[Callable[[], datetime]] = None,
) -> ScoredIssue:
    """
    Score an issue according to Part B specification.
    Starts at 50, applies signals, clamped to 0–100.
    Produces at most 6 friendly reasons.
    """
    now = now_fn() if now_fn else get_current_time()
    status, status_reasons = determine_status(issue, now)

    score = INITIAL_SCORE
    reasons = list(status_reasons)

    # Positive Signal: Good first issue label
    has_gfi = labels_match(issue.labels, GOOD_FIRST_ISSUE_TAGS)
    if has_gfi:
        score += WEIGHT_GOOD_FIRST_ISSUE
        reasons.append("Labelled as beginner-friendly")

    # Positive Signal: Help wanted label
    has_hw = labels_match(issue.labels, HELP_WANTED_TAGS)
    if has_hw:
        score += WEIGHT_HELP_WANTED
        reasons.append("Maintainers are actively looking for help")

    # Body signals
    body_raw = issue.body or ""
    body_len = len(body_raw)

    if OPTIMAL_BODY_MIN <= body_len <= OPTIMAL_BODY_MAX:
        score += WEIGHT_BODY_OPTIMAL_LENGTH
        reasons.append("Good description length")
    elif body_len > LONG_BODY_THRESHOLD:
        score += WEIGHT_BODY_OVERLY_LONG
        reasons.append("Very long issue description")

    # Helpful body content
    has_code_block = "```" in body_raw
    has_file_path = bool(RE_FILE_PATH.search(body_raw))
    body_lower = body_raw.lower()
    has_steps_or_expected = (
        "steps to reproduce" in body_lower
        or "expected" in body_lower
        or "expected behavior" in body_lower
    )

    if has_code_block or has_file_path or has_steps_or_expected:
        score += WEIGHT_HELPFUL_BODY_CONTENT
        if has_steps_or_expected:
            reasons.append("Includes reproduction steps or expected behavior")
        elif has_file_path or has_code_block:
            reasons.append("Provides code context or file references")

    # Maintainer commented
    maintainer_commented = any(
        (c.author_association or "").upper() in MAINTAINER_ASSOCIATIONS
        for c in issue.comments
    )
    if maintainer_commented:
        score += WEIGHT_MAINTAINER_COMMENTED
        reasons.append("A repository maintainer has replied")

    # Updated in the last 30 days
    updated_dt = _parse_iso_datetime(issue.updated_at)
    if updated_dt:
        age_days = (now - updated_dt).total_seconds() / 86400.0
        if age_days <= DAYS_RECENT_ACTIVITY:
            score += WEIGHT_RECENTLY_UPDATED
            reasons.append("Active in the last 30 days")

    # Excessive comments (> 15)
    if issue.comments_count > HIGH_COMMENTS_THRESHOLD:
        score += WEIGHT_EXCESSIVE_COMMENTS
        reasons.append("Long ongoing discussion in comments")

    # Difficult labels
    for lbl in issue.labels:
        lbl_lower = lbl.lower()
        if any(diff in lbl_lower for diff in DIFFICULT_LABEL_KEYWORDS):
            score += WEIGHT_DIFFICULT_LABELS
            reasons.append(f"Label '{lbl}' indicates advanced complexity")
            break

    # Status penalties
    if status == "claimed":
        score += WEIGHT_STATUS_CLAIMED
    elif status == "stale":
        score += WEIGHT_STATUS_STALE
    elif status == "unclear":
        score += WEIGHT_STATUS_UNCLEAR

    # Clamp score
    clamped_score = max(SCORE_MIN, min(SCORE_MAX, score))

    # Deduplicate reasons while preserving order, cap at MAX_REASONS
    deduped_reasons = []
    seen = set()
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped_reasons.append(r)
            if len(deduped_reasons) >= MAX_REASONS:
                break

    return ScoredIssue(
        issue=issue,
        score=clamped_score,
        status=status,
        reasons=deduped_reasons,
        ai=None,
    )


def rank(
    issues: list[Issue],
    now_fn: Optional[Callable[[], datetime]] = None,
) -> list[ScoredIssue]:
    """
    Rank issues:
    Status order: safe, unclear, stale, claimed.
    Score descending inside each status.
    """
    status_priority = {
        "safe": 0,
        "unclear": 1,
        "stale": 2,
        "claimed": 3,
    }

    scored_list = [score_issue(i, now_fn=now_fn) for i in issues]
    scored_list.sort(key=lambda s: (status_priority.get(s.status, 99), -s.score))
    return scored_list
