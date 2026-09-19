from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.services.store import get_store

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("caer")

@asynccontextmanager
async def lifespan(_: FastAPI):
    store = get_store()
    log.info("%s %s ready - %d simulation(s), %d project(s)", settings.app_name,
             settings.version, len(store.simulation_ids()), len(store.list_projects()))
    if not store.simulation_ids():
        log.warning("no datasets found in %s - run scripts/generate_samples.py",
                    settings.samples_dir)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.version,
    description=(
        "Solver-independent CAE post-processing API. Results from any adapter are mapped into "
        "one common model and analysed by domain-agnostic engines."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "version": settings.version,
            "docs": "/docs", "api": "/api/health"}
