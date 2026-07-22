"""Auth helpers — JWT bearer carrying agent_id."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncIterator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db.session import async_session_factory, set_agent_context
from urie.config import get_settings

security = HTTPBearer(auto_error=False)


class AgentPrincipal(BaseModel):
    agent_id: str
    name: Optional[str] = None


def create_access_token(agent_id: str, name: Optional[str] = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": agent_id, "name": name or agent_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_agent(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> AgentPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        agent_id = payload.get("sub")
        if not agent_id:
            raise HTTPException(status_code=401, detail="Invalid token: no agent_id")
        return AgentPrincipal(agent_id=agent_id, name=payload.get("name"))
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def get_agent_session(
    agent: Annotated[AgentPrincipal, Depends(get_current_agent)],
) -> AsyncIterator[AsyncSession]:
    """DB session with app.agent_id set so RLS policies bind to the caller."""
    async with async_session_factory() as session:
        await set_agent_context(session, agent.agent_id)
        try:
            yield session
        finally:
            # Clear so pooled connections are not sticky to a tenant.
            await set_agent_context(session, "")
