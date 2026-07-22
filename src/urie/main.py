"""FastAPI application factory."""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from urie.api.v1.router import api_router
from urie.adapters.db.session import async_session_factory, engine, init_db
from urie.config import get_settings
from sqlalchemy import text

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SPAStaticFiles(StaticFiles):
    """Serve the built app shell for client-side routes."""

    async def get_response(self, path: str, scope: dict) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404 and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Local dev only — never auto-create schema on Vercel/serverless cold starts.
    if settings.app_env == "development" and not os.environ.get("VERCEL"):
        await init_db()
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="URIE — Unified Relational Intelligence Engine",
        version="0.1.0",
        description="Relationship Intelligence core: debrief → graph → ghost-mode feed",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/v1")

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db", include_in_schema=False)
    async def health_db() -> JSONResponse | dict[str, str]:
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                agents = await session.scalar(text("SELECT to_regclass('public.agents')"))
                if agents is None:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "status": "error",
                            "error": "SchemaNotMigrated",
                            "detail": "Database is reachable but tables are missing. Run: alembic upgrade head",
                        },
                    )
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "error": type(exc).__name__,
                    "detail": str(exc)[:300],
                },
            )
        return {"status": "ok", "database": "connected"}

    # Mount UI after /v1 so API routes take priority.
    if STATIC_DIR.is_dir():
        app.mount("/", SPAStaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
    return app


app = create_app()
