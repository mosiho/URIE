"""RLS session binding smoke test against live Postgres."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from urie.adapters.db import models as m
from urie.adapters.db.session import set_agent_context
from urie.services.ingestion import IngestionService


@pytest.mark.asyncio
async def test_rls_isolates_agents(session):
    """With FORCE RLS + app.agent_id, agent A cannot read agent B's nodes."""
    a = IngestionService(session)
    await a.start_debrief("agt_rls_a", transcript="Met with Alice. Alice's budget is 1 million USD.")
    await session.commit()

    b = IngestionService(session)
    await b.start_debrief("agt_rls_b", transcript="Met with Bob. Bob's budget is 2 million USD.")
    await session.commit()

    # Bind as agent A — should only see Alice
    await set_agent_context(session, "agt_rls_a")
    session.expire_all()
    names_a = {
        n.name
        for n in (
            await session.execute(select(m.Node).where(m.Node.kind == m.NodeKind.PERSON))
        ).scalars().all()
    }
    assert "Alice" in names_a
    assert "Bob" not in names_a

    # Bind as agent B — should only see Bob
    await set_agent_context(session, "agt_rls_b")
    session.expire_all()
    names_b = {
        n.name
        for n in (
            await session.execute(select(m.Node).where(m.Node.kind == m.NodeKind.PERSON))
        ).scalars().all()
    }
    assert "Bob" in names_b
    assert "Alice" not in names_b

    # Clear binding — empty agent_id policy allows all (ops/tests)
    await set_agent_context(session, "")
    session.expire_all()
    names_all = {
        n.name
        for n in (
            await session.execute(select(m.Node).where(m.Node.kind == m.NodeKind.PERSON))
        ).scalars().all()
    }
    assert "Alice" in names_all and "Bob" in names_all
