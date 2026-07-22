"""Initial schema: agents, facts, nodes, edges, embeddings, debriefs, feed, outbox, er_config."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create enum types once, then reference them with create_type=False so
    # create_table does not try to recreate them.
    node_kind = postgresql.ENUM(
        "Person", "Trait", "Constraint", name="node_kind", create_type=False
    )
    edge_type = postgresql.ENUM(
        "RELATES_TO",
        "HAS_TRAIT",
        "CONSTRAINED_BY",
        "DECIDES_FOR",
        name="edge_type",
        create_type=False,
    )
    debrief_status = postgresql.ENUM(
        "active",
        "awaiting_resolution",
        "completed",
        "failed",
        name="debrief_status",
        create_type=False,
    )
    feed_status = postgresql.ENUM(
        "active", "held", "acked", "dismissed", name="feed_status", create_type=False
    )

    bind = op.get_bind()
    for enum in (node_kind, edge_type, debrief_status, feed_status):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("agent_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "nodes",
        sa.Column("node_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("kind", node_kind, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("attrs", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_touched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_nodes_agent_id", "nodes", ["agent_id"])
    op.create_index("ix_nodes_agent_kind", "nodes", ["agent_id", "kind"])
    op.create_index("ix_nodes_agent_name", "nodes", ["agent_id", "name"])

    op.create_table(
        "facts",
        sa.Column("fact_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("entity", sa.String(128), nullable=False),
        sa.Column("subject_node_id", sa.String(64), sa.ForeignKey("nodes.node_id"), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("is_hypothesis", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_conflict_resolution", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("superseded_by", sa.String(64), sa.ForeignKey("facts.fact_id"), nullable=True),
    )
    op.create_index("ix_facts_agent_id", "facts", ["agent_id"])
    op.create_index("ix_facts_agent_subject_entity", "facts", ["agent_id", "subject_node_id", "entity"])

    op.create_table(
        "edges",
        sa.Column("edge_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("edge_type", edge_type, nullable=False),
        sa.Column("src_node_id", sa.String(64), sa.ForeignKey("nodes.node_id"), nullable=False),
        sa.Column("dst_node_id", sa.String(64), sa.ForeignKey("nodes.node_id"), nullable=False),
        sa.Column("fact_id", sa.String(64), sa.ForeignKey("facts.fact_id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rel_label", sa.String(128), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attrs", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_edges_agent_id", "edges", ["agent_id"])
    op.create_index("ix_edges_agent_src", "edges", ["agent_id", "src_node_id"])
    op.create_index("ix_edges_agent_dst", "edges", ["agent_id", "dst_node_id"])
    op.create_index("ix_edges_agent_type", "edges", ["agent_id", "edge_type"])

    op.create_table(
        "node_embeddings",
        sa.Column("node_id", sa.String(64), sa.ForeignKey("nodes.node_id"), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("embedding", Vector(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_node_embeddings_agent_id", "node_embeddings", ["agent_id"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_node_embeddings_hnsw "
        "ON node_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "debrief_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("status", debrief_status, nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False, server_default=""),
        sa.Column("staged_mutations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pending_challenge", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_debrief_sessions_agent_id", "debrief_sessions", ["agent_id"])

    op.create_table(
        "feed_items",
        sa.Column("feed_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("subject_node_id", sa.String(64), sa.ForeignKey("nodes.node_id"), nullable=False),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("gifting_suggestion", sa.Text(), nullable=True),
        sa.Column("status", feed_status, nullable=False),
        sa.Column("held_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_event_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_feed_items_agent_id", "feed_items", ["agent_id"])
    op.create_index("ix_feed_agent_status", "feed_items", ["agent_id", "status"])

    op.create_table(
        "outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_agent_id", "outbox", ["agent_id"])
    op.create_index("ix_outbox_unprocessed", "outbox", ["processed_at"])

    op.create_table(
        "er_config",
        sa.Column("config_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("w1", sa.Float(), nullable=False),
        sa.Column("w2", sa.Float(), nullable=False),
        sa.Column("w3", sa.Float(), nullable=False),
        sa.Column("lambda_decay", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "version", name="uq_er_config_agent_version"),
    )
    op.create_index("ix_er_config_agent_id", "er_config", ["agent_id"])

    op.create_table(
        "crm_writebacks",
        sa.Column("writeback_id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("fact_id", sa.String(64), sa.ForeignKey("facts.fact_id"), nullable=False, unique=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("crm_target", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_crm_writebacks_agent_id", "crm_writebacks", ["agent_id"])


def downgrade() -> None:
    op.drop_table("crm_writebacks")
    op.drop_table("er_config")
    op.drop_table("outbox")
    op.drop_table("feed_items")
    op.drop_table("debrief_sessions")
    op.drop_table("node_embeddings")
    op.drop_table("edges")
    op.drop_table("facts")
    op.drop_table("nodes")
    op.drop_table("agents")
    sa.Enum(name="feed_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="debrief_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="edge_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="node_kind").drop(op.get_bind(), checkfirst=True)
