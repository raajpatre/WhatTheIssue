import re


def normalize_label(s: str) -> str:
    text = s.lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def labels_match(issue_labels: list[str], tags: list[str]) -> bool:
    labels = {normalize_label(label) for label in issue_labels}
    return any(normalize_label(tag) in labels for tag in tags)
