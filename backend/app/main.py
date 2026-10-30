from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config as _config  # noqa: F401
from app.api import health, issues, repos, watch
from app.api.errors import AppError, error_body
from app.db.session import init_db
from app.github.client import close_http_client
from app.github.exceptions import RateLimitError, RepoNotFoundError, UpstreamError
from app.watcher.service import start_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    start_scheduler()
    yield
    close_http_client()


app = FastAPI(title="myOpenSource", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(repos.router, prefix="/api")
app.include_router(issues.router, prefix="/api")
app.include_router(watch.router, prefix="/api")


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(ValueError)
async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_body("INVALID_REPO", str(exc)))


@app.exception_handler(RateLimitError)
async def handle_rate_limit(_request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=error_body("RATE_LIMITED", str(exc) or "GitHub rate limit exceeded"),
    )


@app.exception_handler(RepoNotFoundError)
async def handle_github_not_found(_request: Request, exc: RepoNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("REPO_NOT_FOUND", str(exc) or "Repository not found"),
    )


@app.exception_handler(UpstreamError)
async def handle_upstream(_request: Request, exc: UpstreamError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=error_body("UPSTREAM_ERROR", str(exc) or "Upstream error"),
    )
