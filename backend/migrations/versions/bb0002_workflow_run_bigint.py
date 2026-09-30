"""Support GitHub workflow run IDs larger than a 32-bit integer."""
from alembic import op
import sqlalchemy as sa

revision = "bb0002"
down_revision = "56b779327f8b"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite INTEGER is already 64-bit; retaining it avoids rebuilding referenced tables.
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("workflow_runs", "source_run_id", type_=sa.BigInteger(), existing_type=sa.Integer())


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("workflow_runs", "source_run_id", type_=sa.Integer(), existing_type=sa.BigInteger())
