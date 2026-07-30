"""FastAPI application entry point."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.public import public_router
from .api.v1 import api_router
from .core.config import settings
from .db.base import Base
from .db.session import engine

DISCLAIMER = (
    "AutoBid Intelligence provides decision support only. Recommendations are estimates, not "
    "guarantees; results depend on the accuracy of entered and third-party data. A physical and "
    "mechanical inspection may still be required. Users remain responsible for bidding decisions."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenience for dev/first-run: create tables if they do not exist. In production the
    # Alembic migrations own the schema (run before the app boots via docker-compose command).
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)  # uploaded storefront photos
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=f"UK vehicle-auction decision-support API.\n\n**{DISCLAIMER}**",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:16])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Security headers.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _error(status_code: int, code: str, message: str, request: Request, fields=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
                "fields": fields,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, f"http_{exc.status_code}", str(exc.detail), request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = {".".join(str(p) for p in e["loc"][1:]): e["msg"] for e in exc.errors()}
    return _error(422, "validation_error", "Request validation failed", request, fields)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Sanitised: never leak internals to the client.
    return _error(500, "internal_error", "An unexpected error occurred.", request)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": settings.api_title, "version": settings.api_version}


@app.get("/", tags=["meta"])
async def root():
    return {"service": settings.api_title, "docs": "/docs", "disclaimer": DISCLAIMER}


app.include_router(api_router)
app.include_router(public_router)

# Serve uploaded storefront photos. In production, point media_dir at a persistent volume/bucket mount.
app.mount("/media", StaticFiles(directory=settings.media_dir, check_dir=False), name="media")
