"""SQLAlchemy models for the URIE tri-store (collapsed into Postgres)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class NodeKind(str, enum.Enum):
    PERSON = "Person"
    TRAIT = "Trait"
    CONSTRAINT = "Constraint"


class EdgeType(str, enum.Enum):
    RELATES_TO = "RELATES_TO"
    HAS_TRAIT = "HAS_TRAIT"
    CONSTRAINED_BY = "CONSTRAINED_BY"
    DECIDES_FOR = "DECIDES_FOR"


class DebriefStatus(str, enum.Enum):
    ACTIVE = "active"
    INTERVIEWING = "interviewing"
    AWAITING_RESOLUTION = "awaiting_resolution"
    COMPLETED = "completed"
    FAILED = "failed"


class FeedStatus(str, enum.Enum):
    ACTIVE = "active"
    HELD = "held"
    ACKED = "acked"
    DISMISSED = "dismissed"


def _uuid() -> str:
    return str(uuid4())


class Agent(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Fact(Base):
    __tablename__ = "facts"
    __table_args__ = (
        Index("ix_facts_agent_subject_entity", "agent_id", "subject_node_id", "entity"),
    )

    fact_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"fct_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="voice_debrief")
    is_hypothesis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_conflict_resolution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_by: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("facts.fact_id"), nullable=True
    )


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index("ix_nodes_agent_kind", "agent_id", "kind"),
        Index("ix_nodes_agent_name", "agent_id", "name"),
    )

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"node_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    kind: Mapped[NodeKind] = mapped_column(
        Enum(
            NodeKind,
            name="node_kind",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_touched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    embedding: Mapped[Optional["NodeEmbedding"]] = relationship(back_populates="node", uselist=False)


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        Index("ix_edges_agent_src", "agent_id", "src_node_id"),
        Index("ix_edges_agent_dst", "agent_id", "dst_node_id"),
        Index("ix_edges_agent_type", "agent_id", "edge_type"),
    )

    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"edge_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    edge_type: Mapped[EdgeType] = mapped_column(
        Enum(
            EdgeType,
            name="edge_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    src_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), nullable=False)
    dst_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), nullable=False)
    fact_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("facts.fact_id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    rel_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # spouse, attorney, etc.
    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NodeEmbedding(Base):
    __tablename__ = "node_embeddings"

    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    embedding = mapped_column(Vector(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    node: Mapped["Node"] = relationship(back_populates="embedding")


class DebriefSession(Base):
    __tablename__ = "debrief_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"deb_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    status: Mapped[DebriefStatus] = mapped_column(
        Enum(
            DebriefStatus,
            name="debrief_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DebriefStatus.ACTIVE,
    )
    transcript: Mapped[str] = mapped_column(Text, nullable=False, default="")
    staged_mutations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pending_challenge: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Multi-turn interview fields (Alembic 0003)
    turns: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    covered_gaps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    next_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="oneshot")  # oneshot|interview
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = (Index("ix_feed_agent_status", "agent_id", "status"),)

    feed_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"feed_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    subject_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gifting_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[FeedStatus] = mapped_column(
        Enum(
            FeedStatus,
            name="feed_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=FeedStatus.ACTIVE,
    )
    held_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox"
    __table_args__ = (Index("ix_outbox_unprocessed", "processed_at"),)

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"evt_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ERConfig(Base):
    """Versioned entity-resolution weights (§5.2)."""

    __tablename__ = "er_config"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_er_config_agent_version"),)

    config_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"erc_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    w1: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)  # JaroWinkler
    w2: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)  # Jaccard overlap
    w3: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)  # recency decay
    lambda_decay: Mapped[float] = mapped_column(Float, nullable=False, default=0.01)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CRMWriteback(Base):
    """Idempotent CRM write-back log (keyed on fact_id)."""

    __tablename__ = "crm_writebacks"

    writeback_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"wb_{_uuid()}")
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.agent_id"), nullable=False, index=True)
    fact_id: Mapped[str] = mapped_column(String(64), ForeignKey("facts.fact_id"), nullable=False, unique=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    crm_target: Mapped[str] = mapped_column(String(64), nullable=False, default="stub")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
