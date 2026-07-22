"""Database engine and session helpers."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from urie.adapters.db.models import Base
from urie.config import get_settings

settings = get_settings()


def _engine_kwargs(database_url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"echo": False, "pool_pre_ping": True}
    connect_args: dict[str, Any] = {}
    is_local = "localhost" in database_url or "127.0.0.1" in database_url
    is_pooler = ":6543" in database_url or "pooler.supabase.com" in database_url

    if not is_local:
        connect_args["ssl"] = "require"
        connect_args["statement_cache_size"] = 0
        if is_pooler:
            connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"

    if os.environ.get("VERCEL"):
        kwargs["poolclass"] = NullPool

    if connect_args:
        kwargs["connect_args"] = connect_args
    return kwargs


engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

TENANT_TABLES = (
    "facts",
    "nodes",
    "edges",
    "node_embeddings",
    "debrief_sessions",
    "feed_items",
    "outbox",
)


async def set_agent_context(session: AsyncSession, agent_id: Optional[str]) -> None:
    """
    Bind Postgres RLS to the authenticated agent for this connection.

    Uses session-level set_config (is_local=false) so the binding survives
    mid-request commits inside application services.
    """
    await session.execute(
        text("SELECT set_config('app.agent_id', :agent_id, false)"),
        {"agent_id": agent_id or ""},
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """Bare session (no RLS binding). Prefer get_agent_session in authenticated routes."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Create extensions and tables (dev convenience; prefer Alembic in prod)."""
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            # App role (urie_app) is not a superuser — extension must already exist
            # from migrations / docker init. Continue with tables + RLS.
            pass
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_rls(conn)


async def _ensure_rls(conn) -> None:
    """Enable FORCE ROW LEVEL SECURITY + agent_id policies on tenant tables."""
    for table in TENANT_TABLES:
        await conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                  ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY;
                  ALTER TABLE IF EXISTS {table} FORCE ROW LEVEL SECURITY;
                EXCEPTION WHEN OTHERS THEN
                  NULL;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{table}' AND policyname = '{table}_agent_isolation'
                  ) THEN
                    CREATE POLICY {table}_agent_isolation ON {table}
                      USING (
                        current_setting('app.agent_id', true) IS NULL
                        OR current_setting('app.agent_id', true) = ''
                        OR agent_id = current_setting('app.agent_id', true)
                      )
                      WITH CHECK (
                        current_setting('app.agent_id', true) IS NULL
                        OR current_setting('app.agent_id', true) = ''
                        OR agent_id = current_setting('app.agent_id', true)
                      );
                  END IF;
                EXCEPTION WHEN OTHERS THEN
                  NULL;
                END $$;
                """
            )
        )
