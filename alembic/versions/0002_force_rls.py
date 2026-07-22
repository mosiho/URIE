"""Enable FORCE ROW LEVEL SECURITY on tenant tables."""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_force_rls"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "facts",
    "nodes",
    "edges",
    "node_embeddings",
    "debrief_sessions",
    "feed_items",
    "outbox",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
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
            END $$;
            """
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_agent_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
