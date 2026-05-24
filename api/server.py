# api/server.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: add auth token before any external exposure
"""FastAPI app for the internal PRANIK benchmark dashboard."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import benchmark, failures, routing, scorecards


app = FastAPI(
    title="PRANIK Benchmark API",
    description="Internal developer dashboard API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(benchmark.router, prefix="/api/benchmark", tags=["benchmark"])
app.include_router(scorecards.router, prefix="/api/scorecards", tags=["scorecards"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(failures.router, prefix="/api/failures", tags=["failures"])

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
