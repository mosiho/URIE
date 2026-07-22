"""FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles

from urie.api.v1.router import api_router
from urie.adapters.db.session import engine, init_db
from urie.config import get_settings

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
    if settings.app_env == "development":
        await init_db()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="URIE — Unified Relational Intelligence Engine",
        version="0.1.0",
        description="Relationship Intelligence core: debrief → graph → ghost-mode feed",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/v1")
    # Mount UI after /v1 so API routes take priority.
    app.mount("/", SPAStaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
    return app


app = create_app()
