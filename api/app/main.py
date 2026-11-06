"""FastAPI application factory, middleware, structured logging, and error handlers."""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import (
    auth,
    categories,
    channels,
    feed,
    me,
    ops,
    playlists,
    search,
    videos,
    youtube_sync,
)
from app.schemas.common import ProblemDetails

# Structured logging configuration
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger("mytube.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("application_startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Middleware: Request ID & Request logging
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["x-request-id"] = req_id

        logger.info(
            "http_request",
            request_id=req_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    # RFC 9457 Problem Details Exception Handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        problem = ProblemDetails(
            type=f"{settings.PUBLIC_BASE_URL}/errors/{exc.status_code}",
            title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            status=exc.status_code,
            detail=str(exc.detail),
            instance=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(),
            media_type="application/problem+json",
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for err in exc.errors():
            loc = ".".join(str(l) for l in err.get("loc", []) if l != "body")
            msg = err.get("msg", "Validation error")
            messages.append(f"{loc}: {msg}" if loc else msg)
        detail_msg = "; ".join(messages)
        problem = ProblemDetails(
            type=f"{settings.PUBLIC_BASE_URL}/errors/422",
            title="Validation Error",
            status=422,
            detail=detail_msg,
            instance=request.url.path,
        )
        return JSONResponse(
            status_code=422,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )

    # Ops & Metrics at root
    app.include_router(ops.router)

    # REST API v1 router
    from fastapi import APIRouter

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(me.router)
    api_v1.include_router(categories.router)
    api_v1.include_router(feed.router)
    api_v1.include_router(videos.router)
    api_v1.include_router(channels.router)
    api_v1.include_router(playlists.router)
    api_v1.include_router(search.router)
    api_v1.include_router(youtube_sync.router)
    api_v1.include_router(ops.router)

    app.include_router(api_v1)

    return app


app = create_app()
