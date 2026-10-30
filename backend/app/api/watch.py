from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.db import crud
from app.github.client import parse_repo
from app.schemas import Watch, WatchIn
from app.watcher.service import baseline_repo, check_all_now

router = APIRouter()


@router.post("/watch")
async def create_watch(body: WatchIn) -> Watch:
    normalized = body.model_copy(update={"repo": parse_repo(body.repo)})
    watch = crud.create_watch(normalized)
    await run_in_threadpool(baseline_repo, watch.repo)
    return watch


@router.get("/watch")
async def list_watches(contact: str | None = Query(default=None)) -> list[Watch]:
    return crud.list_watches(contact=contact)


@router.post("/watch/check-now")
async def watch_check_now() -> dict:
    return await run_in_threadpool(check_all_now)


@router.delete("/watch/{id}")
async def delete_watch(id: int) -> dict:
    crud.delete_watch(id)
    return {"ok": True}
