#!/usr/bin/env python3
"""
scripts/demo_create_issue.py — Part C (P0)

Creates ONE new issue with a 'good first issue' label in DEMO_REPO using DEMO_GITHUB_TOKEN.
Event Rule 4 (Fork, don't spam): Refuses to run if target repo is not exactly DEMO_REPO.
This is the ONLY write operation permitted in the entire project.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def load_dotenv() -> None:
    """Load environment variables from .env file if present, without external dependencies."""
    repo_root = Path(__file__).resolve().parent.parent
    env_file = repo_root / ".env"
    if not env_file.is_file():
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


def create_demo_issue(
    target_repo: str | None = None,
    title: str | None = None,
    body: str | None = None,
    labels: list[str] | None = None,
) -> str:
    """
    Creates an issue on GitHub.
    Enforces that target_repo must match DEMO_REPO exactly.
    Returns the created issue HTML URL.
    """
    load_dotenv()

    demo_repo = os.getenv("DEMO_REPO", "").strip()
    demo_token = os.getenv("DEMO_GITHUB_TOKEN", "").strip()

    if not demo_repo:
        raise ValueError("DEMO_REPO environment variable is not set. Check your .env file.")
    if not demo_token:
        raise ValueError("DEMO_GITHUB_TOKEN environment variable is not set. Check your .env file.")

    # Guard: Target MUST be exactly DEMO_REPO
    effective_repo = (target_repo or demo_repo).strip()
    if effective_repo != demo_repo:
        raise PermissionError(
            f"REFUSAL: Target repo '{effective_repo}' is not DEMO_REPO ('{demo_repo}'). "
            "Write operations are strictly forbidden on any repo except DEMO_REPO."
        )

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    issue_title = title or f"Fix typo in installation guide ({now_str})"
    issue_body = (
        body
        or (
            "### Description\n"
            "In `docs/setup.md` the command `pip instal requests` is missing an 'l'.\n\n"
            "### Steps to reproduce / resolve\n"
            "1. Open `docs/setup.md`\n"
            "2. Change `pip instal` to `pip install`\n"
            "3. Submit a pull request\n\n"
            "This is a starter issue for new contributors!"
        )
    )
    issue_labels = labels or ["good first issue"]

    url = f"https://api.github.com/repos/{demo_repo}/issues"
    headers = {
        "Authorization": f"Bearer {demo_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "myopensource-demo-script",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    payload = {
        "title": issue_title,
        "body": issue_body,
        "labels": issue_labels,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            html_url = data.get("html_url", "")
            return html_url
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        # Scrub any token accidental reflection in message
        safe_msg = f"GitHub API error (HTTP {e.code}): {e.reason} - {error_body}"
        if demo_token and demo_token in safe_msg:
            safe_msg = safe_msg.replace(demo_token, "[REDACTED_TOKEN]")
        raise RuntimeError(safe_msg) from None
    except Exception as e:
        safe_msg = f"Network or request error: {str(e)}"
        if demo_token and demo_token in safe_msg:
            safe_msg = safe_msg.replace(demo_token, "[REDACTED_TOKEN]")
        raise RuntimeError(safe_msg) from None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a test issue in DEMO_REPO for Part C live demo."
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Target repo (must match DEMO_REPO exactly).",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Optional issue title.",
    )
    parser.add_argument(
        "--body",
        type=str,
        default=None,
        help="Optional issue body.",
    )
    args = parser.parse_args()

    try:
        issue_url = create_demo_issue(
            target_repo=args.repo,
            title=args.title,
            body=args.body,
        )
        print(f"✅ Issue successfully created: {issue_url}")
    except PermissionError as pe:
        print(f"❌ Security Violation: {pe}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"❌ Failed to create issue: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
