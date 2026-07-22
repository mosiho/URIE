"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from urie.adapters.db.models import Base
from urie.adapters.db.session import _ensure_rls, set_agent_context
from urie.config import get_settings


async def _postgres_available(url: str) -> bool:
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    """App (non-superuser) URL — used for test sessions so RLS binds."""
    return get_settings().database_url


@pytest.fixture(scope="session")
def admin_database_url() -> str:
    """Admin URL — used to create/drop schema (tables are owned by migrator)."""
    return get_settings().database_url_admin or get_settings().database_url


@pytest_asyncio.fixture
async def db_engine(database_url: str, admin_database_url: str):
    if not await _postgres_available(database_url):
        pytest.skip(
            "Postgres+pgvector not available. Run: docker compose up -d "
            "(requires Docker). Unit tests do not need a database."
        )

    # Schema lifecycle as admin (can DROP tables/enums owned by migrator role).
    admin_engine = create_async_engine(admin_database_url, echo=False, pool_pre_ping=True)
    async with admin_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_rls(conn)
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO urie_app")
        )
        await conn.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO urie_app")
        )
    await admin_engine.dispose()

    # Sessions run as urie_app so FORCE RLS is enforceable.
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    yield engine

    admin_engine = create_async_engine(admin_database_url, echo=False, pool_pre_ping=True)
    async with admin_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await admin_engine.dispose()
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await set_agent_context(session, "")
        yield session
        await session.rollback()
