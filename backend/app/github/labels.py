# NEEDS-FROM-PART-A: backend/app/github/labels.py is owned by Part A.
# Implemented here per AGENTS.md contract so Part B can run independently without waiting.

import re


def normalize_label(s: str) -> str:
    """Lowercase, '-' and '_' become spaces, collapse whitespace."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[-_]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def labels_match(issue_labels: list[str], tags: list[str]) -> bool:
    """Any normalized tag equals any normalized label."""
    if not issue_labels or not tags:
        return False
    norm_labels = {normalize_label(lbl) for lbl in issue_labels}
    for tag in tags:
        if normalize_label(tag) in norm_labels:
            return True
    return False
