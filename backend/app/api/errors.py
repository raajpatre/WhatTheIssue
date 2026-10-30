class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidRepoError(AppError):
    def __init__(self, message: str = "Invalid repository URL or slug") -> None:
        super().__init__("INVALID_REPO", message, 400)


class RepoNotFoundError(AppError):
    def __init__(self, message: str = "Repository not found") -> None:
        super().__init__("REPO_NOT_FOUND", message, 404)


class RateLimitedError(AppError):
    def __init__(self, message: str = "GitHub rate limit exceeded") -> None:
        super().__init__("RATE_LIMITED", message, 429)


class UpstreamError(AppError):
    def __init__(self, message: str = "Upstream error") -> None:
        super().__init__("UPSTREAM_ERROR", message, 502)


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
