from app.schemas import AIInsight, Issue, ReadmeSuggestion


def explain_issue(issue: Issue) -> AIInsight:
    return AIInsight(
        summary="Not explained yet.",
        files_to_touch=[],
        skills_needed=[],
        first_steps=[],
        beginner_rating=5,
        provider="fallback",
    )


def suggest_from_readme(repo: str, readme: str) -> list[ReadmeSuggestion]:
    return [
        ReadmeSuggestion(
            title="Improve the README",
            description="Placeholder suggestion until AI is wired up.",
            area="docs",
            why_beginner_friendly="Docs changes are a common first contribution.",
        )
    ]
